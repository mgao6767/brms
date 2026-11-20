"""Worker jobs, run in this process."""
# ruff: noqa: D103, S101, PLR2004

from __future__ import annotations

import json
from pathlib import Path

import pytest

from brms.web import jobs

_SVB = Path(__file__).resolve().parents[2] / "src" / "brms" / "lab" / "examples" / "svb_call_report_20211231.json"


def test_call_report_build(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import brms.lab.call_report as module

    items = json.loads(_SVB.read_text())
    monkeypatch.setattr(module, "fetch_call_report", lambda _cert, _date: items)
    summary = jobs.build_from_call_report({"cert": 24735, "date": "2021-12-31"}, str(tmp_path))
    assert "SILICON VALLEY BANK" in summary["name"]
    assert summary["start_date"] == "2022-01-01"
    assert summary["unit"] == 1000
    assert float(summary["operating"]["noninterest_expense"]) > 0
    assert (tmp_path / "bank.zip").exists()
    assert json.loads((tmp_path / "summary.json").read_text())["positions"]


@pytest.mark.parametrize(("spec", "label"), [
    ({"kind": "historical"}, "Historical rates"),
    ({"kind": "basel", "name": "steepener"}, "Steepener"),
    ({"kind": "parallel", "bp": -100, "ramp_days": 90}, "Parallel -100bp, phased in over 90 days"),
])
def test_describe(spec: dict, label: str) -> None:
    assert jobs.describe(spec) == label
    jobs.scenario_from_spec(spec)


def test_negative_ramp_is_rejected() -> None:
    with pytest.raises(jobs.SpecError, match="ramp_days"):
        jobs.scenario_from_spec({"kind": "parallel", "bp": 100, "ramp_days": -1})


def test_worker_marks_its_run_as_started(tmp_path: Path) -> None:
    from brms.web.workspace import Workspace

    workspace = Workspace(tmp_path)
    meta = workspace.create_run({"id": "demo-x", "name": "x"}, {"kind": "historical"})
    jobs._mark_running(workspace.run_dir(meta["id"]))  # noqa: SLF001
    assert workspace.run_meta(meta["id"])["status"] == "running"
    workspace.update_run(meta["id"], status="done")
    jobs._mark_running(workspace.run_dir(meta["id"]))  # noqa: SLF001
    assert workspace.run_meta(meta["id"])["status"] == "done"  # never overwrites an outcome


def test_summary_reads_unit_and_story_from_the_zip(tmp_path: Path) -> None:
    from brms.data.create_case_studies import CASE_STUDIES, create_case_study

    case = next(c for c in CASE_STUDIES if c.slug == "svb_2021")
    data = tmp_path / "market"
    data.mkdir()
    zip_path = create_case_study(case, data)
    summary = jobs.summarise_bank(str(zip_path), str(tmp_path / "summary.json"))
    assert summary["unit"] == 1000
    assert summary["story"] == case.story
    assert summary["name"] == "Silicon Valley Bank, end-2021"
    assert float(summary["operating"]["noninterest_expense"]) > 0
