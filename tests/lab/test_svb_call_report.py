"""SVB built from its own Call Report alone, run through 2022 (docs/lab/validation.md).

HTM is within 3 percentage points of the end-2022 Call Report. AFS loses more than reported: the
data does not give each book's maturity profile, so AFS gets the bank's overall (long) profile.
"""
# ruff: noqa: D103, S101, PLR2004

from __future__ import annotations

from typing import TYPE_CHECKING

from brms.lab.examples.svb_call_report import REPORTED_2022, run_case

if TYPE_CHECKING:
    from pathlib import Path


def test_svb_from_its_call_report(tmp_path: Path) -> None:
    outcome = run_case(tmp_path)
    assert abs(outcome.htm_rate - REPORTED_2022["htm"]) < 0.03
    assert outcome.afs_rate < REPORTED_2022["afs"] < 0
