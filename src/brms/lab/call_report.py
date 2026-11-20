"""Build a bank file from a US bank's Call Report (via the FDIC BankFind financials API).

The Call Report (FFIEC 031/041) gives a bank's balance sheet each quarter, including how its debt
securities and loans spread over remaining-maturity (or next-repricing) buckets. Those buckets are
enough to give the lab a bank with the right interest-rate profile:

* **Securities** (Schedule RC-B, Memorandum 2: HTM at amortised cost plus AFS at fair value).
  Non-mortgage debt per maturity bucket becomes a bullet bond at the bucket midpoint, split between
  Treasuries (sovereign) and other issuers (agency/municipal, treated as PSEs). Mortgage
  pass-throughs per remaining-maturity bucket become agency MBS pools with that remaining term.
  Other MBS (CMOs, CMBS) per expected-average-life bucket become bullets at 2 and 6 years. Each
  class splits between HTM and AFS in the bank's overall proportions, or as given by ``afs`` (the
  data does not say which securities are in which book), so the HTM and AFS totals, and their fair
  values, match the report. All securities carry the bank's securities yield.
* **Loans** (Schedule RC-C, Memorandum 2) by remaining maturity or next repricing, scaled to net
  loans. Loans repricing within 3 months are Prime floaters; the rest are amortising fixed-rate
  loans (1-4 family loans as residential mortgages) at the bucket midpoint, at the loan yield.
* **Funding**: noninterest-bearing deposits; interest-bearing deposits at the bank's deposit cost;
  other borrowings, fed funds purchased and subordinated debt as one floating-rate liability.
* **Equity** is the balancing figure (bank_file); items not modelled (trading assets, premises,
  intangibles, other assets and liabilities) explain its gap to reported equity, which is kept
  under ``"reported"`` with the reported capital figures.

Values stay in USD thousands, as reported. Income items are year-to-date and are annualised.
Deposit behaviour (``beta``, ``runoff_rate``) is left at zero for the user to set.
"""

from __future__ import annotations

import datetime
import json
import urllib.parse
import urllib.request
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

API = "https://api.fdic.gov/banks/financials"

# (bucket key, FDIC suffix, bond maturity in years, MBS remaining term, loan remaining term)
_BUCKETS = (
    ("3les", "3LES", 0.125, "2M", "2M"),
    ("3t12", "3T12", 0.625, "8M", "8M"),
    ("1t3", "1T3", 2.0, "2Y", "2Y"),
    ("3t5", "3T5", 4.0, "4Y", "4Y"),
    ("5t15", "5T15", 10.0, "10Y", "10Y"),
    ("ov15", "OV15", 20.0, "25Y", "20Y"),
)
_OTHER_MBS = (("3yles", "SCO3YLES", 2.0), ("ov3y", "SCOOV3Y", 6.0))
_REPORTED = ("ASSET", "EQ", "RBCT1C", "RBCT1CER", "RWAJ", "SCHA", "SCHF", "SCAA", "SCAF", "INTAN", "TRADE")

FIELDS: tuple[str, ...] = (
    "CERT", "NAME", "REPDTE", "ASSET", "EQ", "CHBAL", "FREPO", "TRADE", "INTAN",
    "SC", "SC5", "SCHA", "SCHF", "SCAA", "SCAF", "SCUST", "SCO3YLES", "SCOOV3Y",
    *(f"SCPT{s}" for _k, s, *_ in _BUCKETS), *(f"SCNM{s}" for _k, s, *_ in _BUCKETS),
    "LNLSNET", "LNLSGR", "LNLSGR5",
    *(f"LNRS{s}" for _k, s, *_ in _BUCKETS), *(f"LNOT{s}" for _k, s, *_ in _BUCKETS),
    "DEP", "DEPNIDOM", "OTHBRF", "FREPP", "SUBND", "EDEP", "EINTEXP", "ISC", "ILNLS",
    "RBCT1C", "RBCT1CER", "RWAJ",
)

_TREASURY = {"name": "US Treasury", "issuer_type": "SOVEREIGN", "credit_rating": "AA_PLUS"}
_AGENCY = {"name": "US agencies and municipalities", "issuer_type": "PSE", "credit_rating": "AA_PLUS"}
_BORROWERS = {"name": "Commercial and consumer borrowers", "issuer_type": "CORPORATE"}
_HOUSEHOLDS = {"name": "1-4 family borrowers", "issuer_type": "INDIVIDUAL"}


def fetch_call_report(
    cert: int, date: str | datetime.date, *, get: Callable[[str], bytes] | None = None,
) -> dict[str, Any]:
    """Return the Call Report items (``FIELDS``) of FDIC certificate *cert* for quarter-end *date*.

    Raises:
        LookupError: the FDIC has no filing for that bank and date.

    """
    day = date if isinstance(date, datetime.date) else datetime.date.fromisoformat(date)
    query = urllib.parse.urlencode({
        "filters": f"CERT:{cert} AND REPDTE:{day:%Y%m%d}", "fields": ",".join(FIELDS), "format": "json",
        "limit": 1,
    })
    url = f"{API}?{query}"
    payload = json.loads((get or _get)(url))
    rows = payload.get("data") or []
    if not rows:
        msg = f"No Call Report for FDIC certificate {cert} on {day} (dates are quarter ends)"
        raise LookupError(msg)
    items = dict(rows[0]["data"])
    items.pop("ID", None)
    return items


def _get(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "brms", "Accept": "application/json"})  # noqa: S310
    with urllib.request.urlopen(request, timeout=60) as response:  # noqa: S310
        return response.read()


def _n(items: dict[str, Any], key: str) -> float:
    value = items.get(key)
    return 0.0 if value is None else float(value)


def _ratio(numerator: float, denominator: float, what: str) -> float:
    if denominator <= 0:
        msg = f"Cannot compute {what}: the denominator is {denominator}"
        raise ValueError(msg)
    return numerator / denominator


def bank_file_from_call_report(
    items: dict[str, Any],
    *,
    prime: float,
    ltv: float = 0.8,
    aoci_filter: bool = True,
    afs: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Return a bank file (see :mod:`brms.lab.bank_file`) built from Call Report *items*.

    Args:
        items: Call Report items as returned by :func:`fetch_call_report` (USD thousands).
        prime: The Prime rate on the report date (decimal), to set floating loans' spread.
        ltv: Loan-to-value ratio assumed for 1-4 family mortgages (credit risk weight).
        aoci_filter: Whether AOCI is excluded from CET1 (true for most US banks below $700bn).
        afs: AFS fair value by class (``treasury``, ``other_debt``, ``pass_through``, ``other_mbs``),
            e.g. from the 10-K or FR Y-9C, scaled to the reported AFS total. Each class is then
            AFS in that proportion and HTM for the rest. Without it every class splits in the
            bank's overall HTM : AFS proportion; the Call Report data used here does not say which
            securities are in which book.

    """
    as_of = datetime.datetime.strptime(str(items["REPDTE"]), "%Y%m%d").date()  # noqa: DTZ007
    annualise = 12 / as_of.month
    positions = [
        *_securities(items, as_of, _ratio(_n(items, "ISC") * annualise, _n(items, "SC5"), "the securities yield"),
                     afs),
        *_loans(items, as_of, _ratio(_n(items, "ILNLS") * annualise, _n(items, "LNLSGR5"), "the loan yield"),
                prime, ltv),
    ]
    return {
        "name": f"{items.get('NAME', 'Bank')} (Call Report {as_of}, USD thousands)",
        "as_of": as_of.isoformat(),
        "source": {"provider": "FDIC BankFind financials (Call Report)", "cert": items.get("CERT"),
                   "report_date": as_of.isoformat()},
        "reported": {k: items.get(k) for k in _REPORTED},
        "regulatory": {"aoci_filter": aoci_filter},
        "cash": _n(items, "CHBAL") + _n(items, "FREPO"),
        "deposits": _funding(items, annualise),
        "positions": positions,
    }


AFS_CLASSES = ("treasury", "other_debt", "pass_through", "other_mbs")


def _afs_fractions(
    totals: dict[str, float], items: dict[str, Any], afs: dict[str, float] | None,
) -> dict[str, float]:
    """Return the AFS share of each security class (the rest is HTM)."""
    afs_fair, htm_cost = _n(items, "SCAF"), _n(items, "SCHA")
    if afs is None:
        share = _ratio(afs_fair, htm_cost + afs_fair, "the AFS share of securities")
        return dict.fromkeys(AFS_CLASSES, share)
    unknown = set(afs) - set(AFS_CLASSES)
    if unknown:
        msg = f"Unknown AFS classes {sorted(unknown)}; use {', '.join(AFS_CLASSES)}"
        raise ValueError(msg)
    scale = _ratio(afs_fair, sum(afs.values()), "the AFS composition")
    return {c: min(1.0, afs.get(c, 0.0) * scale / totals[c]) if totals[c] else 0.0 for c in AFS_CLASSES}


def _securities(
    items: dict[str, Any], as_of: datetime.date, coupon: float, afs: dict[str, float] | None,
) -> list[dict[str, Any]]:
    htm_cost, htm_fair = _n(items, "SCHA"), _n(items, "SCHF")
    afs_cost, afs_fair = _n(items, "SCAA"), _n(items, "SCAF")

    def bond(years: float, issuer: dict[str, str]) -> dict[str, Any]:
        maturity = as_of + datetime.timedelta(days=round(years * 365.25))
        return {"type": "fixed_rate_bond", "coupon_rate": coupon, "issue_date": as_of.isoformat(),
                "maturity_date": maturity.isoformat(), "issuer": issuer}

    non_mortgage = sum(_n(items, f"SCNM{s}") for _k, s, *_ in _BUCKETS)
    treasury_share = min(1.0, _n(items, "SCUST") / non_mortgage) if non_mortgage else 0.0
    # (class, position id, amount: HTM at amortised cost + AFS at fair value, instrument terms)
    pieces: list[tuple[str, str, float, dict[str, Any]]] = []
    for key, suffix, years, pool_term, _loan_term in _BUCKETS:
        amount = _n(items, f"SCNM{suffix}")
        pieces.append(("treasury", f"nm-{key}-ust", amount * treasury_share, bond(years, _TREASURY)))
        pieces.append(("other_debt", f"nm-{key}-oth", amount * (1 - treasury_share), bond(years, _AGENCY)))
        pieces.append(("pass_through", f"pt-{key}", _n(items, f"SCPT{suffix}"), {
            "type": "mortgage_backed_security", "coupon_rate": coupon, "issue_date": as_of.isoformat(),
            "maturity": pool_term, "issuer": _AGENCY,
        }))
    for key, field, years in _OTHER_MBS:
        pieces.append(("other_mbs", f"omb-{key}", _n(items, field), bond(years, _AGENCY)))

    totals = dict.fromkeys(AFS_CLASSES, 0.0)
    for cls, _pid, amount, _terms in pieces:
        totals[cls] += amount
    fractions = _afs_fractions(totals, items, afs)
    out: list[dict[str, Any]] = []
    for cls, pid, amount, terms in pieces:
        held, available = amount * (1 - fractions[cls]), amount * fractions[cls]
        if held > 0:
            out.append({"id": f"{pid}-htm", **terms, "face_value": held, "basis": "AMORTIZED_COST",
                        "amortized_cost": held, "fair_value": held * _ratio(htm_fair, htm_cost, "HTM fair value")})
        if available > 0:
            cost = available * _ratio(afs_cost, afs_fair, "AFS amortised cost")
            out.append({"id": f"{pid}-afs", **terms, "face_value": cost, "basis": "FVOCI",
                        "amortized_cost": cost, "fair_value": available})
    return out


def _loans(
    items: dict[str, Any], as_of: datetime.date, rate: float, prime: float, ltv: float,
) -> list[dict[str, Any]]:
    gross = sum(_n(items, f"{p}{s}") for p in ("LNRS", "LNOT") for _k, s, *_ in _BUCKETS)
    scale = _ratio(_n(items, "LNLSNET"), gross, "the loan scaling") if gross else 0.0
    out: list[dict[str, Any]] = []
    for prefix, pid, issuer in (("LNRS", "rs", _HOUSEHOLDS), ("LNOT", "ln", _BORROWERS)):
        for key, suffix, _years, _pool, term in _BUCKETS:
            amount = _n(items, f"{prefix}{suffix}") * scale
            if amount <= 0:
                continue
            common = {"id": f"{pid}-{key}", "face_value": amount, "issue_date": as_of.isoformat(),
                      "issuer": issuer, "basis": "AMORTIZED_COST", "amortized_cost": amount}
            if key == "3les":
                out.append({**common, "type": "variable_rate_loan", "spread": rate - prime, "maturity": "3Y",
                            "benchmark_family": "prime", "repricing_frequency": "1M", "payment_frequency": "1M",
                            "principal_repayment_mode": "bullet"})
            elif prefix == "LNRS":
                out.append({**common, "type": "residential_mortgage", "interest_rate": rate, "maturity": term,
                            "ltv": ltv})
            else:
                out.append({**common, "type": "amortizing_fixed_rate_loan", "interest_rate": rate,
                            "maturity": term, "frequency": "1M"})
    return out


def _funding(items: dict[str, Any], annualise: float) -> list[dict[str, Any]]:
    noninterest = _n(items, "DEPNIDOM")
    interest_bearing = _n(items, "DEP") - noninterest
    deposit_cost = _n(items, "EDEP") * annualise
    out = [{"id": "nib", "name": "Noninterest-bearing deposits", "balance": noninterest, "interest_rate": 0.0}]
    if interest_bearing > 0:
        out.append({"id": "ib", "name": "Interest-bearing deposits", "balance": interest_bearing,
                    "interest_rate": deposit_cost / interest_bearing})
    borrowed = _n(items, "OTHBRF") + _n(items, "FREPP") + _n(items, "SUBND")
    if borrowed > 0:
        cost = max(0.0, _n(items, "EINTEXP") * annualise - deposit_cost)
        out.append({"id": "borrowings", "name": "Other borrowings", "balance": borrowed,
                    "interest_rate": cost / borrowed, "beta": 1.0})
    return out
