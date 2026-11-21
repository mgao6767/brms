"""Build the case-study banks from the Call Reports saved in ``call_reports/`` (public FDIC data).

Each case is a real bank's balance sheet at a quarter end, mapped by :mod:`brms.lab.call_report`
and written as ``case_<slug>.zip`` next to the other default simulations::

    uv run python -m brms.data.create_case_studies
"""

from __future__ import annotations

import datetime
import json
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from brms.data import DEFAULT_DATA_FOLDER

CALL_REPORTS = Path(__file__).with_name("call_reports")


@dataclass(frozen=True)
class CaseStudy:
    """A saved Call Report and how to present it."""

    slug: str
    name: str
    story: str
    aoci_filter: bool = True


CASE_STUDIES = (
    CaseStudy("svb_2021", "Silicon Valley Bank, end-2021",
              "A $209bn bank with $125bn of long, fixed-rate securities funded by uninsured deposits. "
              "Run it through 2022 to watch the unrealised losses that sank it in March 2023."),
    CaseStudy("svb_2022", "Silicon Valley Bank, end-2022",
              "SVB ten weeks before it failed: $15bn of unrealised losses on held-to-maturity securities, "
              "invisible in its regulatory capital because of the AOCI filter."),
    CaseStudy("signature_2021", "Signature Bank, end-2021",
              "A $118bn bank that failed two days after SVB, funded heavily by uninsured deposits."),
    CaseStudy("first_republic_2021", "First Republic Bank, end-2021",
              "A $181bn bank whose long fixed-rate mortgages lost value as rates rose; it failed in May 2023."),
    CaseStudy("jpmorgan_chase_2021", "JPMorgan Chase Bank, end-2021",
              "The largest US bank, for comparison. Advanced-approaches banks count AOCI in CET1.",
              aoci_filter=False),
)


def create_case_study(case: CaseStudy, data_folder: Path = DEFAULT_DATA_FOLDER) -> Path:
    """Build ``case_<slug>.zip`` for *case* and return its path."""
    from brms.lab.bank_file import build_bank, default_market_frames, prime_on
    from brms.lab.call_report import bank_file_from_call_report

    items = json.loads((CALL_REPORTS / f"{case.slug}.json").read_text())
    report_date = datetime.datetime.strptime(str(items["REPDTE"]), "%Y%m%d").date()  # noqa: DTZ007
    frames = default_market_frames()
    bank = bank_file_from_call_report(items, prime=prime_on(frames, report_date), aoci_filter=case.aoci_filter)
    bank["name"] = case.name
    bank["story"] = case.story
    out = data_folder.parent / f"case_{case.slug}.zip"
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / f"{case.slug}.json"
        path.write_text(json.dumps(bank))
        build_bank(path, frames, out)
    return out


def create_case_study_zips(data_folder: Path = DEFAULT_DATA_FOLDER) -> list[Path]:
    """Build every case study and return the zip paths."""
    return [create_case_study(case, data_folder) for case in CASE_STUDIES]


if __name__ == "__main__":
    folder = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DATA_FOLDER
    for zip_path in create_case_study_zips(folder):
        print(f"Created {zip_path}")  # noqa: T201
