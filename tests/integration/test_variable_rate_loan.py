"""Integration test: simulate a Prime + spread C&I loan for 3 months."""

from __future__ import annotations

import datetime
import json
import zipfile
from pathlib import Path

import pandas as pd
import pytest
import QuantLib as ql  # noqa: N813

from brms.core.enums import TransactionType


def _build_test_zip(tmp_path: Path) -> Path:
    """Build a zip with one variable-rate loan + equity funding."""
    config = {"name": "CI Loan Test", "start_date": "2024-01-02", "end_date": "2024-04-01"}

    instruments = [
        {"id": "equity-001", "type": "common_equity", "name": "Bank Equity"},
        {
            "id": "ci-loan-001",
            "type": "variable_rate_loan",
            "name": "Prime+250bp CI Loan",
            "face_value": 10000000.0,
            "issue_date": "2024-01-02",
            "maturity": "5Y",
            "spread": 0.025,
            "benchmark_family": "prime",
            "repricing_frequency": "1M",
            "payment_frequency": "1M",
            "principal_repayment_mode": "bullet",
            "measurement_basis": "AMORTIZED_COST",
            "book_type": "banking",
            "credit_rating": "BBB",
        },
    ]

    positions = [
        {
            "id": "pos-equity", "instrument_id": "equity-001", "book_type": "BANKING",
            "measurement_basis": "NA", "side": "SHORT",
            "acquisition_date": "2024-01-02", "acquisition_cost": 2000000,
        },
        {
            "id": "pos-loan", "instrument_id": "ci-loan-001", "book_type": "BANKING",
            "measurement_basis": "AMORTIZED_COST", "side": "LONG",
            "acquisition_date": "2024-01-02", "acquisition_cost": 10000000,
        },
    ]

    balances = {
        "balances": {
            "Cash and Cash Equivalents": 0,
            "Shareholders' Equity": 2000000,
            "Loans and Advances": 10000000,
        },
        "valuations": {"pos-loan": {"carrying_value": 10000000}},
    }

    # Build yield and benchmark CSVs covering the simulation window
    bdays = pd.bdate_range("2024-01-02", "2024-04-01")
    yields_df = pd.DataFrame({
        "3 Mo": [5.3] * len(bdays),
        "6 Mo": [5.2] * len(bdays),
        "1 Yr": [5.0] * len(bdays),
        "2 Yr": [4.8] * len(bdays),
        "5 Yr": [4.5] * len(bdays),
        "10 Yr": [4.3] * len(bdays),
    }, index=bdays)
    yields_df.index.name = "date"

    prime_rates = [8.50 if d < pd.Timestamp("2024-02-01") else 8.75 for d in bdays]
    bench_df = pd.DataFrame({"DPRIME": prime_rates}, index=bdays)
    bench_df.index.name = "date"

    zip_path = tmp_path / "ci_loan_test.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("config.json", json.dumps(config))
        zf.writestr("instruments.json", json.dumps(instruments))
        zf.writestr("positions.json", json.dumps(positions))
        zf.writestr("balances.json", json.dumps(balances))
        zf.writestr("yields.csv", yields_df.to_csv())
        zf.writestr("benchmarks.csv", bench_df.to_csv())
    return zip_path


@pytest.fixture(autouse=True)
def _clear_ql_state():
    yield
    ql.IndexManager.instance().clearHistories()


class TestVariableRateLoanIntegration:
    def test_simulation_produces_interest_accrual_transactions(self, tmp_path) -> None:
        from brms.core.services import build_core_services

        zip_path = _build_test_zip(tmp_path)
        services = build_core_services(simulation_zip=zip_path)

        sim = services.simulation_service
        start = sim.start_date

        advanced = 0
        for i in range(10):
            d = start + datetime.timedelta(days=i + 1)
            if services.market_data.has_data(d):
                sim.advance(d)
                advanced += 1

        assert advanced > 0

        accruals = [
            t for t in services.transaction_log.all()
            if t.type == TransactionType.INTEREST_ACCRUAL and t.instrument_id == "ci-loan-001"
        ]
        assert len(accruals) > 0
        assert all(t.amount > 0 for t in accruals)

    def test_variable_loan_carrying_value_computed(self, tmp_path) -> None:
        from brms.core.enums import ValuationType
        from brms.core.services import build_core_services

        zip_path = _build_test_zip(tmp_path)
        services = build_core_services(simulation_zip=zip_path)

        cv = services.valuation_store.get("pos-loan", services.simulation_service.start_date, ValuationType.CARRYING_VALUE)
        assert cv is not None
        assert float(cv) == pytest.approx(10_000_000, rel=0.01)


class TestRegressionExistingFixedRate:
    def test_default_htm_treasury_still_loads(self) -> None:
        from brms.core.services import build_core_services

        services = build_core_services()
        assert services.bank is not None
        assert len(list(services.bank.positions.open_positions())) > 0
