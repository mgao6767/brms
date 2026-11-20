"""SVB from its own Call Report: the bank (Silicon Valley Bank, FDIC certificate 24735) at 31 Dec 2021.

Unlike :mod:`brms.lab.examples.svb`, which rebuilds the holding company's 10-K balance sheet by
hand, this case uses only the bank's Call Report as the FDIC publishes it (saved alongside this
module as ``svb_call_report_20211231.json``, so it runs offline) through
:mod:`brms.lab.call_report`. The bank is run through actual 2022 yields and its unrealised losses,
as a share of amortised cost, are compared with its Call Report at 31 Dec 2022:

======  ===============  ==========  ===========
Book    Amortised cost   Fair value  Unrealised
======  ===============  ==========  ===========
HTM     91,327,000       76,168,000  -16.6%
AFS     28,502,000       25,976,000  -8.9%
======  ===============  ==========  ===========

(USD thousands.) Two cases: the Call Report alone, where every security class splits between HTM
and AFS in the bank's overall proportion, and the same with the AFS mix from SVB Financial's 10-K
(mostly Treasuries), since the Call Report data used does not say which securities are in which
book. Run ``python -m brms.lab.examples.svb_call_report``.
"""

from __future__ import annotations

import datetime
import json
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from brms.lab.bank_file import build_bank, default_market_frames, prime_on
from brms.lab.call_report import bank_file_from_call_report
from brms.lab.runner import run
from brms.lab.scenarios import Historical

CALL_REPORT = Path(__file__).with_name("svb_call_report_20211231.json")
END = datetime.date(2022, 12, 30)  # last market day of 2022
# AFS fair value by class at 31 Dec 2021, 10-K FY2021 Note 9 (USD thousands): Treasuries; agency
# debentures and foreign government debt; agency residential MBS; agency CMOs and CMBS.
AFS_10K_2021 = {"treasury": 15_850_000, "other_debt": 257_000, "pass_through": 8_589_000, "other_mbs": 2_525_000}
REPORTED_2022 = {"htm": (76_168_000 - 91_327_000) / 91_327_000, "afs": (25_976_000 - 28_502_000) / 28_502_000}


@dataclass(frozen=True)
class Outcome:
    """Engine unrealised loss rates of the HTM and AFS books at the end of 2022."""

    htm_rate: float
    afs_rate: float


def bank(afs: dict[str, float] | None = None) -> dict:
    """Return SVB's bank file built from its end-2021 Call Report (with an optional AFS mix)."""
    items = json.loads(CALL_REPORT.read_text())
    as_of = datetime.datetime.strptime(str(items["REPDTE"]), "%Y%m%d").date()  # noqa: DTZ007
    return bank_file_from_call_report(items, prime=prime_on(default_market_frames(), as_of), afs=afs)


def run_case(workdir: Path, afs: dict[str, float] | None = None) -> Outcome:
    """Build the bank, run 2022 and return the loss rates of the HTM and AFS books."""
    data = bank(afs)
    path = workdir / "svb_call_report.json"
    path.write_text(json.dumps(data))
    result = run(build_bank(path, default_market_frames(), workdir / "svb_call_report.zip"), Historical(), end=END)
    rates = {}
    for book, suffix in (("htm", "-htm"), ("afs", "-afs")):
        ids = [f"pos-{p['id']}" for p in data["positions"] if p["id"].endswith(suffix)]
        fair = result.fair_value[ids].iloc[-1].dropna()
        cost = result.amortized_cost[fair.index].iloc[-1]
        rates[book] = float((fair - cost).sum() / cost.sum())
    return Outcome(rates["htm"], rates["afs"])


def main() -> int:
    """Print the comparison."""
    with tempfile.TemporaryDirectory() as tmp:
        cases = {"call report only": run_case(Path(tmp)), "with 10-K AFS mix": run_case(Path(tmp), AFS_10K_2021)}
    sys.stdout.write(f"{'case':<20}{'HTM':>8}{'reported':>10}{'AFS':>8}{'reported':>10}\n")
    for label, o in cases.items():
        sys.stdout.write(f"{label:<20}{o.htm_rate:>8.1%}{REPORTED_2022['htm']:>10.1%}"
                         f"{o.afs_rate:>8.1%}{REPORTED_2022['afs']:>10.1%}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
