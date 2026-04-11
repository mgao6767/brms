"""Tests for SimulationBuilder."""

from __future__ import annotations

import datetime
from decimal import Decimal

import pandas as pd

from brms.core.enums import BookType, MeasurementBasis, PositionSide
from brms.core.models.position import Position


class TestSimulationBuilder:
    """Tests for SimulationBuilder.build()."""

    def test_build_produces_snapshot_with_balances(self) -> None:
        """Builder runs the engine and produces non-empty balances."""
        from brms.core.services.simulation_builder import BuildConfig, SimulationBuilder

        instruments, positions = _equity_and_deposit()
        yields_df = _minimal_yields(
            start=datetime.date(2024, 1, 1),
            end=datetime.date(2024, 1, 5),
        )

        config = BuildConfig(
            name="Test Bank",
            start_date=datetime.date(2024, 1, 5),
            instruments=instruments,
            positions=positions,
            market_frames={"yields": yields_df},
        )

        snapshot = SimulationBuilder().build(config)

        assert snapshot.name == "Test Bank"  # noqa: S101
        assert snapshot.start_date == datetime.date(2024, 1, 5)  # noqa: S101
        assert len(snapshot.balances) > 0  # noqa: S101
        assert "Cash and Cash Equivalents" in snapshot.balances  # noqa: S101
        assert snapshot.balances["Cash and Cash Equivalents"] > 0  # noqa: S101

    def test_snapshot_preserves_instruments_and_positions(self) -> None:
        """Snapshot carries through the original instruments and positions."""
        from brms.core.services.simulation_builder import BuildConfig, SimulationBuilder

        instruments, positions = _equity_and_deposit()
        yields_df = _minimal_yields(
            start=datetime.date(2024, 1, 1),
            end=datetime.date(2024, 1, 5),
        )

        config = BuildConfig(
            name="Test Bank",
            start_date=datetime.date(2024, 1, 5),
            instruments=instruments,
            positions=positions,
            market_frames={"yields": yields_df},
        )

        snapshot = SimulationBuilder().build(config)

        assert snapshot.instruments is instruments  # noqa: S101
        assert snapshot.positions is positions  # noqa: S101


def _equity_and_deposit() -> tuple[list, list]:
    """Return minimal instrument and position lists for testing."""
    from brms.core.models.instruments.deposits import Deposit
    from brms.core.models.instruments.equity import CommonEquity

    equity_inst = CommonEquity()
    equity_inst.id = "equity-1"
    equity_inst.name = "Common Equity"

    deposit_inst = Deposit()
    deposit_inst.id = "deposit-1"
    deposit_inst.name = "Customer Deposit"

    instruments = [equity_inst, deposit_inst]

    equity_pos = Position(
        id="pos-equity-1",
        instrument_id="equity-1",
        book_type=BookType.BANKING,
        measurement_basis=MeasurementBasis.NA,
        side=PositionSide.SHORT,
        acquisition_date=datetime.date(2024, 1, 1),
        acquisition_cost=Decimal("100000"),
    )
    deposit_pos = Position(
        id="pos-deposit-1",
        instrument_id="deposit-1",
        book_type=BookType.BANKING,
        measurement_basis=MeasurementBasis.NA,
        side=PositionSide.SHORT,
        acquisition_date=datetime.date(2024, 1, 1),
        acquisition_cost=Decimal("500000"),
    )

    return instruments, [equity_pos, deposit_pos]


def _minimal_yields(start: datetime.date, end: datetime.date) -> pd.DataFrame:
    """Build a minimal yields DataFrame covering start..end."""
    dates = pd.date_range(start, end, freq="B")
    columns = [
        "1 Mo", "2 Mo", "3 Mo", "4 Mo", "6 Mo",
        "1 Yr", "2 Yr", "3 Yr", "5 Yr", "7 Yr", "10 Yr", "20 Yr", "30 Yr",
    ]
    data = {col: [0.04] * len(dates) for col in columns}
    return pd.DataFrame(data, index=dates)
