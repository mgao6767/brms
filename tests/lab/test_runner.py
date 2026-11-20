"""Running simulations through scenarios, in-process and in worker processes."""
# ruff: noqa: D103

from __future__ import annotations

import datetime
import json
import subprocess
import sys
from pathlib import Path

import pytest

from brms.core.metrics.risk.interest_rate_risk.eve import Scenario
from brms.core.models.regulatory import RegulatoryConfig
from brms.core.services import build_core_services
from brms.lab.runner import RunResult, run, run_many
from brms.lab.scenarios import Historical, Shock

_DATA = Path(__file__).resolve().parents[2] / "src" / "brms" / "data"
_CI = _DATA / "ci_loan_prime.zip"
_DIVERSIFIED = _DATA / "diversified_bank.zip"


def test_historical_run_equals_stepping_the_engine_by_hand() -> None:
    result = run(_CI, Historical(), months=2)
    services = build_core_services(simulation_zip=_CI)
    sim = services.simulation_service
    while sim.current_date < result.end:
        sim.advance()
    expected = services.reporting_service.balance_sheet(services.bank.ledger, date=result.end)
    assert result.balance_sheet["total_assets"] == pytest.approx(expected["total_assets"])  # noqa: S101
    assert isinstance(result, RunResult)  # noqa: S101
    assert result.metrics.index.max().date() <= result.end  # noqa: S101


def test_runs_in_worker_processes_match_runs_in_this_process() -> None:
    scenarios = [Historical(), Shock(Scenario.PARALLEL_UP)]
    parallel = run_many(_CI, scenarios, months=2, workers=2)
    for scenario, remote in zip(scenarios, parallel, strict=True):
        local = run(_CI, scenario, months=2)
        assert remote.name == scenario.name  # noqa: S101
        assert remote.balance_sheet["total_assets"] == pytest.approx(local.balance_sheet["total_assets"])  # noqa: S101
        assert remote.income_statement["net_income"] == pytest.approx(local.income_statement["net_income"])  # noqa: S101


def test_rate_rise_lowers_cet1_through_aoci_unless_filtered() -> None:
    base = run(_DIVERSIFIED, Historical(), months=3)
    shocked = run(_DIVERSIFIED, Shock(Scenario.PARALLEL_UP), months=3)
    filtered = run(_DIVERSIFIED, Shock(Scenario.PARALLEL_UP), months=3,
                   regulatory=RegulatoryConfig(aoci_filter=True))
    end = base.metrics.index.max()
    assert shocked.metrics.loc[end, "CET1_CAPITAL"] < base.metrics.loc[end, "CET1_CAPITAL"]  # noqa: S101
    assert filtered.metrics.loc[end, "CET1_CAPITAL"] > shocked.metrics.loc[end, "CET1_CAPITAL"]  # noqa: S101


def test_summary_headlines() -> None:
    result = run(_CI, Shock(Scenario.PARALLEL_UP), months=1)
    summary = result.summary
    keys = {"scenario", "start", "end", "cet1_ratio_end", "cet1_ratio_min", "cet1_ratio_min_date",
            "worst_delta_eve_to_tier1", "net_income"}
    assert set(summary) >= keys  # noqa: S101
    assert summary["scenario"] == "parallel_up"  # noqa: S101
    assert datetime.date.fromisoformat(summary["end"]) == result.end  # noqa: S101


def test_cli_writes_results(tmp_path: Path) -> None:
    out = tmp_path / "out"
    cmd = [sys.executable, "-m", "brms.lab", "run", str(_CI), "--scenario", "historical",
           "--scenario", "parallel+200", "--months", "1", "--out", str(out)]
    subprocess.run(cmd, check=True, capture_output=True)  # noqa: S603
    for name in ("historical", "parallel_up"):
        folder = out / name
        for file in ("metrics.csv", "carrying_value.csv", "fair_value.csv", "summary.json"):
            assert (folder / file).exists(), folder / file  # noqa: S101
        assert json.loads((folder / "summary.json").read_text())["scenario"] == name  # noqa: S101


def test_run_can_schedule_a_sale() -> None:
    services = build_core_services(simulation_zip=_DIVERSIFIED)
    fvoci = next(p.id for p in services.bank.positions.open_positions() if p.measurement_basis.name == "FVOCI")
    day = datetime.date(2022, 2, 15)
    result = run(_DIVERSIFIED, Shock(Scenario.PARALLEL_UP), months=2, sales={fvoci: day})
    assert fvoci not in result.carrying_value.columns[result.carrying_value.iloc[-1].notna()]  # noqa: S101
    sold = result.carrying_value[fvoci].dropna()
    assert sold.index.max().date() == day  # noqa: S101  (last valued on the sale date)
