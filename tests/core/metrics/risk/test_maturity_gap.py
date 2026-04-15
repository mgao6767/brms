# ruff: noqa: S101, PLR2004
"""Tests for the Maturity Gap Model."""

from __future__ import annotations

import datetime
from decimal import Decimal
from unittest.mock import MagicMock

from brms.core.enums import BookType, InstrumentType, MeasurementBasis, PositionSide
from brms.core.metrics.risk.interest_rate_risk.maturity_gap import MaturityGapModel, MaturityGapResult
from brms.core.models.position import Position


def _make_instrument(
    instrument_id: str,
    inst_type: InstrumentType,
    maturity_date: datetime.date | None = None,
) -> MagicMock:
    inst = MagicMock()
    inst.id = instrument_id
    inst.instrument_type = inst_type
    inst.repricing_frequency = None
    inst.maturity_date = maturity_date
    inst.repricing_date.return_value = None
    return inst


def _make_position(  # noqa: PLR0913
    pos_id: str,
    instrument_id: str,
    book_type: BookType,
    side: PositionSide,
    acquisition_cost: float,
    measurement_basis: MeasurementBasis = MeasurementBasis.AMORTIZED_COST,
) -> Position:
    return Position(
        id=pos_id,
        instrument_id=instrument_id,
        book_type=book_type,
        measurement_basis=measurement_basis,
        side=side,
        acquisition_date=datetime.date(2021, 1, 1),
        acquisition_cost=Decimal(str(acquisition_cost)),
    )


def test_basic_gap_computation() -> None:
    """A single LONG bond in banking book produces RSA in the correct bucket."""
    as_of = datetime.date(2024, 1, 4)
    # Bond maturing in ~4 years → 3Y-4Y bucket (index 9)
    bond = _make_instrument("bond-1", InstrumentType.FIXED_RATE_BOND, datetime.date(2028, 1, 4))
    pos = _make_position("pos-1", "bond-1", BookType.BANKING, PositionSide.LONG, 500000)

    bank = MagicMock()
    bank.positions.open_positions.return_value = [pos]
    bank.instruments.get.return_value = bond

    valuation_store = MagicMock()
    valuation_store.get.return_value = None  # fall back to acquisition_cost

    model = MaturityGapModel()
    result = model.compute(bank, as_of, valuation_store)

    assert isinstance(result, MaturityGapResult)
    assert result.rsa[9] == 500000.0  # 3Y-4Y bucket
    assert result.total_rsa == 500000.0
    assert result.total_rsl == 0.0
    assert result.total_gap == 500000.0


def test_excludes_trading_book() -> None:
    """Trading book positions are excluded (IRRBB = banking book only)."""
    as_of = datetime.date(2024, 1, 4)
    bond = _make_instrument("bond-1", InstrumentType.FIXED_RATE_BOND, datetime.date(2028, 1, 4))
    pos = _make_position("pos-1", "bond-1", BookType.TRADING, PositionSide.LONG, 500000)

    bank = MagicMock()
    bank.positions.open_positions.return_value = [pos]
    bank.instruments.get.return_value = bond

    model = MaturityGapModel()
    result = model.compute(bank, as_of, MagicMock(get=MagicMock(return_value=None)))

    assert result.total_rsa == 0.0
    assert result.total_rsl == 0.0


def test_excludes_cash_and_equity() -> None:
    """Cash and equity are non-rate-sensitive and excluded."""
    as_of = datetime.date(2024, 1, 4)
    cash = _make_instrument("cash-1", InstrumentType.CASH)
    equity = _make_instrument("eq-1", InstrumentType.COMMON_EQUITY)

    pos_cash = _make_position("pos-c", "cash-1", BookType.BANKING, PositionSide.LONG, 1000000)
    pos_eq = _make_position("pos-e", "eq-1", BookType.BANKING, PositionSide.SHORT, 500000)

    bank = MagicMock()
    bank.positions.open_positions.return_value = [pos_cash, pos_eq]
    bank.instruments.get.side_effect = lambda iid: {"cash-1": cash, "eq-1": equity}[iid]

    model = MaturityGapModel()
    result = model.compute(bank, as_of, MagicMock(get=MagicMock(return_value=None)))

    assert result.total_rsa == 0.0
    assert result.total_rsl == 0.0


def test_deposit_short_is_rsl() -> None:
    """A SHORT deposit in the banking book is RSL in the overnight bucket."""
    as_of = datetime.date(2024, 1, 4)
    deposit = _make_instrument("dep-1", InstrumentType.DEPOSIT)
    deposit.maturity_date = None  # demand deposit, no maturity
    pos = _make_position("pos-d", "dep-1", BookType.BANKING, PositionSide.SHORT, 6000000)

    bank = MagicMock()
    bank.positions.open_positions.return_value = [pos]
    bank.instruments.get.return_value = deposit

    model = MaturityGapModel()
    result = model.compute(bank, as_of, MagicMock(get=MagicMock(return_value=None)))

    assert result.rsl[0] == 6000000.0  # overnight bucket
    assert result.total_rsl == 6000000.0


def test_delta_nii_computation() -> None:
    """ΔNII = gap * ΔR for each bucket."""
    as_of = datetime.date(2024, 1, 4)
    bond = _make_instrument("bond-1", InstrumentType.FIXED_RATE_BOND, datetime.date(2028, 1, 4))
    pos = _make_position("pos-1", "bond-1", BookType.BANKING, PositionSide.LONG, 1000000)

    bank = MagicMock()
    bank.positions.open_positions.return_value = [pos]
    bank.instruments.get.return_value = bond

    model = MaturityGapModel()
    result = model.compute(bank, as_of, MagicMock(get=MagicMock(return_value=None)))

    # gap in bucket 9 (3Y-4Y) = 1,000,000
    assert abs(result.delta_nii_up[9] - 1000000 * 0.02) < 0.01
    assert abs(result.delta_nii_down[9] - 1000000 * -0.02) < 0.01
