"""A point-in-time bank file becomes a simulation snapshot."""
# ruff: noqa: D103

from __future__ import annotations

import datetime
import json
from typing import TYPE_CHECKING

import pytest

from brms.core.enums import MeasurementBasis, ValuationType
from brms.core.exceptions import SimulationDataError
from brms.core.services import build_core_services
from brms.lab.bank_file import build_bank
from tests.support.engine import flat_yields
from tests.support.reconcile import account_balance, assert_books_reconcile

if TYPE_CHECKING:
    from pathlib import Path

    import pandas as pd

_AS_OF = "2021-06-30"
_GOV = {"name": "US Government", "issuer_type": "SOVEREIGN", "credit_rating": "AAA"}


def _bank(cash: float = 2_000_000.0) -> dict:
    return {
        "name": "Point-in-time Bank",
        "as_of": _AS_OF,
        "regulatory": {"aoci_filter": False, "operational_rwa": "250000"},
        "cash": cash,
        "deposits": [{"id": "dep", "name": "Savings", "balance": 2_500_000.0, "interest_rate": 0.001}],
        "positions": [
            {"id": "ust-htm", "type": "treasury_note", "face_value": 1_000_000.0, "coupon_rate": 0.015,
             "issue_date": "2020-11-15", "maturity_date": "2030-11-15", "issuer": _GOV,
             "basis": "AMORTIZED_COST", "amortized_cost": 980_000.0, "fair_value": 950_000.0},
            {"id": "ust-afs", "type": "treasury_note", "face_value": 500_000.0, "coupon_rate": 0.01,
             "issue_date": "2021-02-15", "maturity_date": "2026-02-15", "issuer": _GOV,
             "basis": "FVOCI", "amortized_cost": 500_000.0, "fair_value": 490_000.0},
            {"id": "mtg", "type": "residential_mortgage", "face_value": 400_000.0, "interest_rate": 0.03,
             "issue_date": "2021-06-30", "maturity": "30Y", "ltv": 0.75,
             "issuer": {"name": "Borrower", "issuer_type": "INDIVIDUAL"},
             "basis": "AMORTIZED_COST", "amortized_cost": 400_000.0},
        ],
    }


def _write(tmp_path: Path, bank: dict) -> Path:
    path = tmp_path / "bank.json"
    path.write_text(json.dumps(bank))
    return path


def _yields() -> pd.DataFrame:
    return flat_yields(datetime.date(2021, 1, 4), datetime.date(2021, 12, 31), 0.015)


def test_bank_file_builds_a_reconciling_snapshot(tmp_path: Path) -> None:
    out = tmp_path / "bank.zip"
    build_bank(_write(tmp_path, _bank()), {"yields": _yields()}, out)
    services = build_core_services(simulation_zip=out)
    sim = services.simulation_service
    assert sim.start_date == datetime.date(2021, 7, 1)  # noqa: S101
    assert float(account_balance(sim, "Cash and Cash Equivalents")) == pytest.approx(2_000_000.0)  # noqa: S101
    assert float(account_balance(sim, "Investment Securities at Amortized Cost")) == pytest.approx(980_000.0, abs=0.01)  # noqa: S101
    assert float(account_balance(sim, "Deposits")) == pytest.approx(2_500_000.0)  # noqa: S101
    assert services.bank.regulatory.operational_rwa == 250_000  # noqa: S101, PLR2004
    for _ in range(20):
        sim.advance()
        assert_books_reconcile(sim, sim.current_date)


def test_reported_fair_values_are_matched_through_spreads(tmp_path: Path) -> None:
    out = tmp_path / "bank.zip"
    build_bank(_write(tmp_path, _bank()), {"yields": _yields()}, out)
    services = build_core_services(simulation_zip=out)
    sim = services.simulation_service
    sim.advance()
    day = sim.current_date
    store = services.valuation_store
    # One day after the as-of date on a flat curve, fair values are within a day's carry of the reported ones.
    assert float(store.get("pos-ust-htm", day, ValuationType.FAIR_VALUE)) == pytest.approx(950_000, abs=150)  # noqa: S101
    assert float(store.get("pos-ust-afs", day, ValuationType.FAIR_VALUE)) == pytest.approx(490_000, abs=150)  # noqa: S101
    aoci = account_balance(sim, "Unrealized OCI Gain") - account_balance(sim, "Unrealized OCI Loss")
    assert float(aoci) == pytest.approx(-10_000, abs=200)  # noqa: S101
    position = services.bank.positions.get("pos-ust-afs")
    assert position.measurement_basis == MeasurementBasis.FVOCI  # noqa: S101


def test_equity_is_the_balancing_figure(tmp_path: Path) -> None:
    out = tmp_path / "bank.zip"
    build_bank(_write(tmp_path, _bank()), {"yields": _yields()}, out)
    services = build_core_services(simulation_zip=out)
    sim = services.simulation_service
    expected = 2_000_000 + 980_000 + 500_000 + 400_000 - 2_500_000
    equity = account_balance(sim, "Shareholders' Equity")
    accrued = account_balance(sim, "Accrued Interest Receivable")
    assert float(equity) == pytest.approx(expected + float(accrued), abs=0.05)  # noqa: S101


def test_negative_equity_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(SimulationDataError, match="equity"):
        build_bank(_write(tmp_path, _bank(cash=-5_000_000.0)), {"yields": _yields()}, tmp_path / "x.zip")


def test_cli_builds_a_bank(tmp_path: Path) -> None:
    import subprocess
    import sys

    out = tmp_path / "cli.zip"
    cmd = [sys.executable, "-m", "brms.lab", "build-bank", str(_write(tmp_path, _bank())), "--out", str(out)]
    subprocess.run(cmd, check=True, capture_output=True)  # noqa: S603
    assert build_core_services(simulation_zip=out).simulation_service.start_date == datetime.date(2021, 7, 1)  # noqa: S101


def _mbs_bank() -> dict:
    bank = _bank()
    bank["positions"].append({
        "id": "mbs", "type": "mortgage_backed_security", "face_value": 600_000.0, "coupon_rate": 0.02,
        "issue_date": _AS_OF, "maturity": "25Y",
        "issuer": {"name": "Agency", "issuer_type": "PSE", "credit_rating": "AA_PLUS"},
        "basis": "FVOCI", "amortized_cost": 600_000.0, "fair_value": 590_000.0,
    })
    return bank


def test_mbs_pricing_speed_defaults_to_the_model_speed_on_the_as_of_date(tmp_path: Path) -> None:
    out = tmp_path / "bank.zip"
    build_bank(_write(tmp_path, _mbs_bank()), {"yields": _yields()}, out)
    services = build_core_services(simulation_zip=out)
    mbs = services.bank.instruments.get("mbs")
    incentive = mbs.wac - (0.015 + mbs.prepayment.mortgage_spread)  # flat 1.5% CMT
    assert mbs.pricing_cpr == pytest.approx(mbs.prepayment.cpr(incentive))  # noqa: S101
    sim = services.simulation_service
    sim.advance()
    fair = services.valuation_store.get("pos-mbs", sim.current_date, ValuationType.FAIR_VALUE)
    assert float(fair) == pytest.approx(590_000, abs=200)  # noqa: S101
    for _ in range(40):
        sim.advance()
        assert_books_reconcile(sim, sim.current_date)


def test_snapshot_fair_values_are_the_reported_ones(tmp_path: Path) -> None:
    out = tmp_path / "bank.zip"
    build_bank(_write(tmp_path, _bank()), {"yields": _yields()}, out)
    services = build_core_services(simulation_zip=out)
    snapshot = services.simulation_service.start_date - datetime.timedelta(days=1)
    store = services.valuation_store
    assert float(store.get("pos-ust-htm", snapshot, ValuationType.FAIR_VALUE)) == pytest.approx(950_000, abs=0.01)  # noqa: S101
    assert float(store.get("pos-ust-afs", snapshot, ValuationType.FAIR_VALUE)) == pytest.approx(490_000, abs=0.01)  # noqa: S101


def test_floating_loan_name_shows_the_spread_in_basis_points() -> None:
    import QuantLib as ql  # noqa: N813

    from brms.core.models.instruments.loans import VariableRateLoan
    from brms.core.services.benchmark_service import BenchmarkService

    index = BenchmarkService(forwarding_handle=ql.RelinkableYieldTermStructureHandle()).prime_index
    loan = VariableRateLoan(face_value=100.0, spread=0.0037, issue_date=ql.Date(31, 12, 2021),
                            maturity=ql.Period(3, ql.Years), ibor_index=index)
    assert loan.name.startswith("Prime+37bp")  # noqa: S101


def test_operating_inputs_reach_the_bank(tmp_path: Path) -> None:
    from decimal import Decimal

    from brms.core.models.operating import OperatingConfig

    bank = {**_bank(), "operating": {"noninterest_expense": 36500, "noninterest_income": 3650, "tax_rate": 0.21}}
    out = tmp_path / "bank.zip"
    build_bank(_write(tmp_path, bank), {"yields": _yields()}, out)
    services = build_core_services(simulation_zip=out)
    assert services.bank.operating == OperatingConfig(Decimal(36500), Decimal(3650), 0.21)  # noqa: S101
    sim = services.simulation_service
    for _ in range(10):
        sim.advance()
    assert float(account_balance(sim, "Operating Expense")) == pytest.approx(1_000, abs=0.01)  # noqa: S101


def test_other_assets_and_liabilities_are_carried_and_weighted(tmp_path: Path) -> None:
    from brms.core.enums import MetricName

    bank = {**_bank(), "other_assets": 300_000.0, "other_liabilities": 100_000.0}
    out = tmp_path / "bank.zip"
    build_bank(_write(tmp_path, bank), {"yields": _yields()}, out)
    services = build_core_services(simulation_zip=out)
    sim = services.simulation_service
    assert float(account_balance(sim, "Other Assets")) == pytest.approx(300_000)  # noqa: S101
    assert float(account_balance(sim, "Other Liabilities")) == pytest.approx(100_000)  # noqa: S101
    plain = tmp_path / "plain"
    plain.mkdir()
    build_bank(_write(plain, _bank()), {"yields": _yields()}, plain / "bank.zip")
    base = build_core_services(simulation_zip=plain / "bank.zip")
    equity = "Shareholders' Equity"
    gap = account_balance(sim, equity) - account_balance(base.simulation_service, equity)
    assert float(gap) == pytest.approx(200_000, abs=0.05)  # noqa: S101
    sim.advance()
    base.simulation_service.advance()
    day = sim.current_date
    extra = services.metric_store.get(MetricName.CREDIT_RWA, day) - base.metric_store.get(MetricName.CREDIT_RWA, day)
    assert float(extra) == pytest.approx(300_000, rel=1e-6)  # noqa: S101
    assert_books_reconcile(sim, day)


def test_intangible_assets_are_deducted_from_cet1(tmp_path: Path) -> None:
    from brms.core.enums import MetricName

    out = tmp_path / "a.zip"
    build_bank(_write(tmp_path, {**_bank(), "intangible_assets": 100_000.0}), {"yields": _yields()}, out)
    services = build_core_services(simulation_zip=out)
    sim = services.simulation_service
    assert float(account_balance(sim, "Intangible Assets")) == pytest.approx(100_000)  # noqa: S101
    sim.advance()
    day = sim.current_date
    equity = services.metric_store.get(MetricName.TOTAL_EQUITY, day)
    cet1 = services.metric_store.get(MetricName.CET1_CAPITAL, day)
    assert float(equity) - float(cet1) == pytest.approx(100_000, abs=0.01)  # noqa: S101
