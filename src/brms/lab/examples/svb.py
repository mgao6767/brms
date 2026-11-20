"""Acceptance case: Silicon Valley Bank through the 2022 rate rise.

SVB Financial Group's balance sheet at 31 December 2021 (Form 10-K FY2021, USD millions) is
rebuilt as a point-in-time bank file and run through actual 2022 Treasury yields. The engine's
unrealised losses on held-to-maturity (HTM) and available-for-sale (AFS) securities at the end of
2022 are compared, as a share of amortised cost, with those SVB reported at 31 December 2022
(Form 10-K FY2022):

========  ===============  ==========  =================
Book      Amortised cost   Fair value  Unrealised (rate)
========  ===============  ==========  =================
HTM 2021  98,202           97,227      -975   (-1.0%)
HTM 2022  91,327           76,169      -15,158 (-16.6%)
AFS 2021  27,370           27,221      -149   (-0.5%)
AFS 2022  28,602           26,069      -2,533 (-8.9%)
========  ===============  ==========  =================

Three cases. In the first two, each book is one fixed-rate bullet bond with the portfolio's
reported weighted-average yield as coupon and a maturity chosen so that its modified duration at
that yield equals a target: the durations SVB reported at the start (HTM 4.1 years, AFS 3.5) and at
the end (6.2 and 3.6, after the extension that actually happened). A bullet bond cannot extend. In
the third, the HTM book, mostly agency MBS, is one pass-through pool (coupon = book yield, note
rate 50bp higher, 25 years remaining, default prepayment model), whose projected prepayments slow
as rates rise. SVB's 2022 trading (AFS sales and purchases, the removal of AFS hedges) is not
replayed, so rates are compared, not amounts.

Run ``python -m brms.lab.examples.svb`` for the comparison table.
"""

from __future__ import annotations

import datetime
import json
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import QuantLib as ql  # noqa: N813

from brms.data import DEFAULT_DATA_FOLDER
from brms.lab.bank_file import build_bank
from brms.lab.runner import run
from brms.lab.scenarios import Historical

AS_OF = datetime.date(2021, 12, 31)
END = datetime.date(2022, 12, 30)  # last market day of 2022

# Form 10-K FY2021 / FY2022, USD millions.
HTM_2021 = {"amortized_cost": 98_202.0, "fair_value": 97_227.0, "yield": 0.0164}
AFS_2021 = {"amortized_cost": 27_370.0, "fair_value": 27_221.0, "yield": 0.0117}
REPORTED_LOSS_RATE_2022 = {"htm": (76_169.0 - 91_327.0) / 91_327.0, "afs": (26_069.0 - 28_602.0) / 28_602.0}
DURATION_2021 = {"htm": 4.1, "afs": 3.5}
DURATION_2022 = {"htm": 6.2, "afs": 3.6}
MBS_TERM_YEARS = 25

_AGENCY = {"name": "US agencies", "issuer_type": "PSE", "credit_rating": "AA_PLUS"}
_TREASURY = {"name": "US Government", "issuer_type": "SOVEREIGN", "credit_rating": "AA_PLUS"}
_BORROWERS = {"name": "Venture and private-bank borrowers", "issuer_type": "CORPORATE"}


def maturity_for_duration(target: float, coupon: float, as_of: datetime.date = AS_OF) -> datetime.date:
    """Return the semi-annual bullet maturity whose modified duration at yield = coupon is closest to *target*."""
    settle = ql.Date(as_of.day, as_of.month, as_of.year)
    best, best_gap = None, float("inf")
    for months in range(6, 361, 1):
        maturity = settle + ql.Period(months, ql.Months)
        schedule = ql.Schedule(settle, maturity, ql.Period(ql.Semiannual), ql.NullCalendar(), ql.Unadjusted,
                               ql.Unadjusted, ql.DateGeneration.Backward, False)  # noqa: FBT003
        bond = ql.FixedRateBond(0, 100.0, schedule, [coupon], ql.Thirty360(ql.Thirty360.BondBasis))
        duration = ql.BondFunctions.duration(bond, coupon, ql.Thirty360(ql.Thirty360.BondBasis), ql.Compounded,
                                             ql.Semiannual, ql.Duration.Modified, settle)
        gap = abs(duration - target)
        if gap < best_gap:
            best, best_gap = maturity, gap
    return datetime.date(best.year(), best.month(), best.dayOfMonth())  # type: ignore[union-attr]


def bank_file(htm_duration: float, afs_duration: float) -> dict:
    """Return SVB's end-2021 balance sheet as a bank file, with the books' durations as given."""
    def book(pid: str, figures: dict, duration: float, issuer: dict, basis: str) -> dict:
        maturity = maturity_for_duration(duration, figures["yield"])
        return {
            "id": pid, "type": "fixed_rate_bond", "face_value": figures["amortized_cost"],
            "coupon_rate": figures["yield"], "issue_date": AS_OF.isoformat(), "maturity_date": maturity.isoformat(),
            "issuer": issuer, "basis": basis,
            "amortized_cost": figures["amortized_cost"], "fair_value": figures["fair_value"],
        }

    return {
        "name": "SVB Financial Group (31 Dec 2021, USD millions)",
        "as_of": AS_OF.isoformat(),
        # SVB excluded AOCI from regulatory capital (the AOCI filter).
        "regulatory": {"aoci_filter": True},
        "cash": 14_586.0,
        "deposits": [
            # Noninterest-bearing demand deposits fell from 125,851 to 80,753 in 2022.
            {"id": "nib", "name": "Noninterest-bearing demand", "balance": 125_851.0, "interest_rate": 0.0,
             "runoff_rate": 0.4437},
            # Interest-bearing deposits: rate 0.13% in 2021, 1.13% in 2022 as the 3M yield rose ~4.4pp.
            {"id": "ib", "name": "Interest-bearing", "balance": 63_352.0, "interest_rate": 0.0013, "beta": 0.23},
        ],
        "positions": [
            book("htm", HTM_2021, htm_duration, _AGENCY, "AMORTIZED_COST"),
            book("afs", AFS_2021, afs_duration, _TREASURY, "FVOCI"),
            {"id": "loans", "type": "variable_rate_loan", "name": "Loans (net)", "face_value": 65_854.0,
             "spread": 0.01, "issue_date": AS_OF.isoformat(), "maturity": "3Y", "benchmark_family": "prime",
             "repricing_frequency": "1M", "payment_frequency": "1M", "principal_repayment_mode": "bullet",
             "issuer": _BORROWERS, "basis": "AMORTIZED_COST", "amortized_cost": 65_854.0},
        ],
    }


def bank_file_mbs() -> dict:
    """Return the end-2021 bank with the HTM book as an agency pass-through pool (AFS as reported at the start)."""
    data = bank_file(DURATION_2021["htm"], DURATION_2021["afs"])
    pool = {
        "id": "htm", "type": "mortgage_backed_security", "name": "HTM agency MBS pool",
        "face_value": HTM_2021["amortized_cost"], "coupon_rate": HTM_2021["yield"], "issue_date": AS_OF.isoformat(),
        "maturity": f"{MBS_TERM_YEARS}Y", "issuer": _AGENCY, "basis": "AMORTIZED_COST",
        "amortized_cost": HTM_2021["amortized_cost"], "fair_value": HTM_2021["fair_value"],
    }
    data["positions"] = [pool if p["id"] == "htm" else p for p in data["positions"]]
    return data


@dataclass(frozen=True)
class Outcome:
    """Engine and reported unrealised loss rates at the end of 2022."""

    label: str
    htm_rate: float
    afs_rate: float

    @property
    def htm_reported(self) -> float:
        """SVB's reported HTM unrealised loss / amortised cost."""
        return REPORTED_LOSS_RATE_2022["htm"]

    @property
    def afs_reported(self) -> float:
        """SVB's reported AFS unrealised loss / amortised cost."""
        return REPORTED_LOSS_RATE_2022["afs"]


def run_case(label: str, durations: dict[str, float], workdir: Path) -> Outcome:
    """Build the bank with *durations*, run 2022 and return the loss rates."""
    return run_bank_case(label, bank_file(durations["htm"], durations["afs"]), workdir)


def run_bank_case(label: str, bank: dict, workdir: Path) -> Outcome:
    """Build *bank*, run 2022 and return the loss rates."""
    path = workdir / f"{label}.json"
    path.write_text(json.dumps(bank))
    frames = {
        "yields": pd.read_csv(DEFAULT_DATA_FOLDER / "treasury_yields.csv", index_col="date", parse_dates=True),
        "benchmarks": pd.read_csv(DEFAULT_DATA_FOLDER / "prime_rates.csv", index_col="date", parse_dates=True),
    }
    simulation = build_bank(path, frames, workdir / f"{label}.zip")
    result = run(simulation, Historical(), end=END)
    htm_cost = result.amortized_cost["pos-htm"].dropna().iloc[-1]
    afs_cost = result.amortized_cost["pos-afs"].dropna().iloc[-1]
    return Outcome(label, result.unrealised("pos-htm") / htm_cost, result.unrealised("pos-afs") / afs_cost)


def main() -> int:
    """Print the comparison for both duration assumptions."""
    with tempfile.TemporaryDirectory() as tmp:
        outcomes = [
            run_case("durations-end-2021", DURATION_2021, Path(tmp)),
            run_case("durations-end-2022", DURATION_2022, Path(tmp)),
            run_bank_case("htm-as-mbs-pool", bank_file_mbs(), Path(tmp)),
        ]
    sys.stdout.write(f"{'case':<22}{'HTM engine':>12}{'HTM SVB':>10}{'AFS engine':>12}{'AFS SVB':>10}\n")
    for o in outcomes:
        sys.stdout.write(
            f"{o.label:<22}{o.htm_rate:>12.1%}{o.htm_reported:>10.1%}{o.afs_rate:>12.1%}{o.afs_reported:>10.1%}\n",
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
