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
* **Funding**: noninterest-bearing deposits; interest-bearing deposits at the bank's deposit cost,
  repricing with ``deposit_beta`` of the 3-month yield;
  other borrowings, fed funds purchased and subordinated debt as one floating-rate liability.
* **Operating flows**: non-interest expense and income, annualised, and the effective tax rate.
* **Operational-risk RWA** estimated with the Basel III standardised approach from a simplified
  business indicator (loss multiplier 1), so capital ratios are not on credit RWA alone.
* **Equity** is the balancing figure (bank_file); items not modelled (trading assets, premises,
  intangibles, other assets and liabilities) explain its gap to reported equity, which is kept
  under ``"reported"`` with the reported capital figures.

Values stay in USD thousands, as reported. Income items are year-to-date and are annualised.
Interest-bearing deposits pass through ``deposit_beta`` (default 0.35) of moves in the 3-month
Treasury yield; noninterest-bearing deposits pay nothing; no deposit runs off unless you say so.
"""

from __future__ import annotations

import datetime
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

API = "https://api.fdic.gov/banks/financials"
FEDERAL_TAX_RATE = 0.21
DEPOSIT_BETA = 0.35

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
    "CERT", "NAME", "REPDTE", "ASSET", "LIAB", "EQ", "CHBAL", "FREPO", "TRADE", "INTAN",
    "SC", "SC5", "SCHA", "SCHF", "SCAA", "SCAF", "SCUST", "SCO3YLES", "SCOOV3Y",
    *(f"SCPT{s}" for _k, s, *_ in _BUCKETS), *(f"SCNM{s}" for _k, s, *_ in _BUCKETS),
    "LNLSNET", "LNLSGR", "LNLSGR5",
    *(f"LNRS{s}" for _k, s, *_ in _BUCKETS), *(f"LNOT{s}" for _k, s, *_ in _BUCKETS),
    "DEP", "DEPNIDOM", "OTHBRF", "FREPP", "SUBND", "EDEP", "EINTEXP", "ISC", "ILNLS",
    "NONIX", "NONII", "ITAX", "IBEFTAX", "NETINC", "INTINC", "ERNAST", "EQCDIV", "DEPDOM", "DEPUNINS", "DEPFOR",
    "EQPP", "RBCT2",
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


_RETRY_STATUS = frozenset({429, 500, 502, 503, 504})
_RETRY_WAITS = (2.0, 5.0, 10.0)


def _get(url: str, sleep: Callable[[float], None] = time.sleep) -> bytes:
    """GET *url*, retrying when the FDIC API is busy (429) or briefly unavailable (5xx)."""
    request = urllib.request.Request(url, headers={"User-Agent": "brms", "Accept": "application/json"})  # noqa: S310
    for wait in (*_RETRY_WAITS, None):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:  # noqa: S310
                return response.read()
        except urllib.error.HTTPError as exc:
            if exc.code not in _RETRY_STATUS or wait is None:
                msg = f"The FDIC API answered {exc.code} {exc.reason} for {url}"
                raise ConnectionError(msg) from exc
            sleep(wait)
        except (urllib.error.URLError, TimeoutError) as exc:
            if wait is None:
                msg = f"Cannot reach the FDIC API ({exc}); check the internet connection"
                raise ConnectionError(msg) from exc
            sleep(wait)
    raise AssertionError  # unreachable: the last attempt returns or raises


def _n(items: dict[str, Any], key: str) -> float:
    value = items.get(key)
    return 0.0 if value is None else float(value)


def _ratio(numerator: float, denominator: float, what: str) -> float:
    if denominator <= 0:
        msg = f"Cannot compute {what}: the denominator is {denominator}"
        raise ValueError(msg)
    return numerator / denominator


def bank_file_from_call_report(  # noqa: PLR0913
    items: dict[str, Any],
    *,
    prime: float,
    ltv: float = 0.8,
    aoci_filter: bool = True,
    afs: dict[str, float] | None = None,
    deposit_beta: float = DEPOSIT_BETA,
    core_deposits: bool = True,
) -> dict[str, Any]:
    """Return a bank file (see :mod:`brms.lab.bank_file`) built from Call Report *items*.

    Args:
        items: Call Report items as returned by :func:`fetch_call_report` (USD thousands).
        prime: The Prime rate on the report date (decimal), to set floating loans' spread.
        ltv: Loan-to-value ratio assumed for 1-4 family mortgages (credit risk weight).
        aoci_filter: Whether AOCI is excluded from CET1 (true for most US banks below $700bn).
        deposit_beta: Share of the change in the 3-month Treasury yield passed to interest-bearing
            deposits (default 0.35, roughly the US average through the 2022-23 tightening).
        core_deposits: Give deposits a stable core for EVE (SRP31 caps, weighted by the insured
            share: insured deposits as retail, uninsured as wholesale).
        afs: AFS fair value by class (``treasury``, ``other_debt``, ``pass_through``, ``other_mbs``),
            e.g. from the 10-K or FR Y-9C, scaled to the reported AFS total. Each class is then
            AFS in that proportion and HTM for the rest. Without it every class splits in the
            bank's overall HTM : AFS proportion; the Call Report data used here does not say which
            securities are in which book.

    """
    if not 0 <= deposit_beta <= 1:
        msg = f"deposit_beta must be in [0, 1], got {deposit_beta}"
        raise ValueError(msg)
    report_date = datetime.datetime.strptime(str(items["REPDTE"]), "%Y%m%d").date()  # noqa: DTZ007
    annualise = 12 / report_date.month
    # A quarter end on a weekend is described as of the Friday before: the last business day, when
    # Prime fixes and the curve exists.
    as_of = report_date - datetime.timedelta(days=max(0, report_date.weekday() - 4))
    securities_yield = _n(items, "ISC") * annualise / _n(items, "SC5") if _n(items, "SC5") > 0 else 0.0
    loan_yield = _n(items, "ILNLS") * annualise / _n(items, "LNLSGR5") if _n(items, "LNLSGR5") > 0 else 0.0
    positions = [*_securities(items, as_of, securities_yield, afs), *_loans(items, as_of, loan_yield, prime, ltv)]
    return {
        "name": f"{items.get('NAME', 'Bank')} (Call Report {report_date}, USD thousands)",
        "as_of": as_of.isoformat(),
        "unit": 1000,  # amounts are USD thousands, as reported
        "source": {"provider": "FDIC BankFind financials (Call Report)", "cert": items.get("CERT"),
                   "report_date": report_date.isoformat()},
        "reported": {k: items.get(k) for k in _REPORTED},
        "regulatory": {
            "aoci_filter": aoci_filter,
            "preferred_equity": _n(items, "EQPP"),
            "tier2": _n(items, "RBCT2"),
            "operational_rwa": operational_rwa(
                net_interest_income=(_n(items, "INTINC") - _n(items, "EINTEXP")) * annualise,
                earning_assets=_n(items, "ERNAST") or _n(items, "ASSET"),
                noninterest_income=_n(items, "NONII") * annualise, unit=1000,
            ),
        },
        "operating": _operating(items, annualise),
        "cash": _n(items, "CHBAL") + _n(items, "FREPO"),
        **_other_balances(items),
        "deposits": _funding(items, annualise, deposit_beta, core=core_deposits),
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
    if htm_cost + afs_fair <= 0:
        return []  # no debt securities

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


# Basel III standardised approach for operational risk (OPE25): marginal coefficients on the business
# indicator, by bucket boundary in currency (the US proposal uses USD 1bn and 30bn).
_BIC_BUCKETS = ((1e9, 0.12), (30e9, 0.15), (float("inf"), 0.18))
_ILDC_CAP = 0.0225  # interest component capped at 2.25% of interest-earning assets
_RWA_PER_CAPITAL = 12.5


def operational_rwa(
    *, net_interest_income: float, earning_assets: float, noninterest_income: float, unit: float = 1.0,
) -> float:
    """Return operational-risk RWA from a simplified business indicator (BI), in the inputs' units.

    BI = min(|net interest income|, 2.25% of earning assets) + non-interest income (a proxy for
    the services and financial components); the capital requirement is the business indicator
    component with the internal loss multiplier at 1, and RWA = 12.5 x capital.
    """
    bi = (min(abs(net_interest_income), _ILDC_CAP * earning_assets) + max(noninterest_income, 0.0)) * unit
    capital, lower = 0.0, 0.0
    for upper, coefficient in _BIC_BUCKETS:
        if bi > lower:
            capital += coefficient * (min(bi, upper) - lower)
        lower = upper
    return _RWA_PER_CAPITAL * capital / unit


def _operating(items: dict[str, Any], annualise: float) -> dict[str, float]:
    """Return the annualised non-interest expense and income and the effective tax rate.

    The tax rate is applicable income taxes over income before taxes; without a positive pre-tax
    income (or a rate outside [0, 50%]) it falls back to the US federal rate. Provisions for credit
    losses are not included: credit losses are not modelled.
    """
    pretax, tax = _n(items, "IBEFTAX"), _n(items, "ITAX")
    rate = tax / pretax if pretax > 0 else FEDERAL_TAX_RATE
    net_income = _n(items, "NETINC")
    payout = min(1.0, max(0.0, _n(items, "EQCDIV") / net_income)) if net_income > 0 else 0.0
    return {
        "noninterest_expense": _n(items, "NONIX") * annualise,
        "noninterest_income": _n(items, "NONII") * annualise,
        "tax_rate": rate if 0 <= rate <= 0.5 else FEDERAL_TAX_RATE,  # noqa: PLR2004
        "dividend_payout": payout,
    }


def _other_balances(items: dict[str, Any]) -> dict[str, float]:
    """Return the assets and liabilities the mapping does not model, so equity matches the report.

    Other assets are total assets less cash, debt securities and net loans (trading assets, premises,
    equity securities and the rest); intangibles (goodwill and others) are carried separately and
    deducted from CET1; other liabilities are total liabilities less deposits and borrowings. All are
    carried unchanged; other assets are risk-weighted at 100%.
    """
    intangibles = _n(items, "INTAN")
    modelled_assets = (_n(items, "CHBAL") + _n(items, "FREPO") + _n(items, "SCHA") + _n(items, "SCAF")
                       + _n(items, "LNLSNET") + intangibles)
    modelled_liabilities = _n(items, "DEP") + _n(items, "OTHBRF") + _n(items, "FREPP") + _n(items, "SUBND")
    return {
        "intangible_assets": intangibles,
        "other_assets": max(0.0, _n(items, "ASSET") - modelled_assets),
        "other_liabilities": max(0.0, _n(items, "LIAB") - modelled_liabilities),
    }


# SRP31.112 caps on stable non-maturity deposits: (share of the balance that may be core, average
# life of the core in years) for retail transactional, retail non-transactional and wholesale.
_CORE_RETAIL_TRANSACTIONAL = (0.9, 5.0)
_CORE_RETAIL_OTHER = (0.7, 4.5)
_CORE_WHOLESALE = (0.5, 4.0)
_SMALL_BANK = 1_000_000  # USD 1bn in thousands: below it the uninsured-deposit memo item is not filed


def _core(items: dict[str, Any], retail: tuple[float, float]) -> dict[str, float]:
    """Return a deposit's core share and average life.

    The retail cap applies to the insured share, the wholesale cap to the uninsured share (all
    uninsured when the filing does not say).
    """
    total = _n(items, "DEP")
    domestic = _n(items, "DEPDOM") or total
    foreign = max(0.0, total - domestic)
    # Banks under $1bn do not report uninsured deposits: a 0 or a missing item means unknown.
    reported = items.get("DEPUNINS") is not None and (_n(items, "DEPUNINS") > 0 or _n(items, "ASSET") >= _SMALL_BANK)
    # Foreign deposits are not insured.
    uninsured = 1.0 if total <= 0 or not reported else min(1.0, (_n(items, "DEPUNINS") + foreign) / total)
    insured = 1.0 - uninsured
    share = insured * retail[0] + uninsured * _CORE_WHOLESALE[0]
    life = (insured * retail[0] * retail[1] + uninsured * _CORE_WHOLESALE[0] * _CORE_WHOLESALE[1]) / share
    return {"core_share": share, "core_maturity": life}


def _funding(
    items: dict[str, Any], annualise: float, deposit_beta: float, *, core: bool = True,
) -> list[dict[str, Any]]:
    noninterest = _n(items, "DEPNIDOM")
    interest_bearing = _n(items, "DEP") - noninterest
    deposit_cost = _n(items, "EDEP") * annualise
    out = [{"id": "nib", "name": "Noninterest-bearing deposits", "balance": noninterest, "interest_rate": 0.0,
            **(_core(items, _CORE_RETAIL_TRANSACTIONAL) if core else {})}]
    if interest_bearing > 0:
        out.append({"id": "ib", "name": "Interest-bearing deposits", "balance": interest_bearing,
                    "interest_rate": deposit_cost / interest_bearing, "beta": deposit_beta,
                    **(_core(items, _CORE_RETAIL_OTHER) if core else {})})
    borrowed = _n(items, "OTHBRF") + _n(items, "FREPP") + _n(items, "SUBND")
    if borrowed > 0:
        cost = max(0.0, _n(items, "EINTEXP") * annualise - deposit_cost)
        out.append({"id": "borrowings", "name": "Other borrowings", "balance": borrowed,
                    "interest_rate": cost / borrowed, "beta": 1.0, "borrowing": True})
    return out
