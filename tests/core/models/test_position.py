"""Tests for the Position dataclass."""

import datetime
from decimal import Decimal

from brms.core.enums import BookType, InstrumentClass, PositionSide, PositionStatus
from brms.core.models.position import Position


def test_position_creation() -> None:
    """Position can be created with all fields."""
    pos = Position(
        id="pos-001",
        instrument_id="bond-001",
        book_type=BookType.BANKING,
        instrument_class=InstrumentClass.HTM,
        side=PositionSide.LONG,
        acquisition_date=datetime.date(2024, 1, 15),
        acquisition_cost=Decimal("100000.00"),
    )
    assert pos.id == "pos-001"  # noqa: S101
    assert pos.instrument_id == "bond-001"  # noqa: S101
    assert pos.book_type == BookType.BANKING  # noqa: S101
    assert pos.instrument_class == InstrumentClass.HTM  # noqa: S101
    assert pos.side == PositionSide.LONG  # noqa: S101
    assert pos.acquisition_date == datetime.date(2024, 1, 15)  # noqa: S101
    assert pos.acquisition_cost == Decimal("100000.00")  # noqa: S101


def test_position_status_default_open() -> None:
    """Position status defaults to OPEN."""
    pos = Position(
        id="pos-002",
        instrument_id="bond-002",
        book_type=BookType.TRADING,
        instrument_class=InstrumentClass.FVTPL,
        side=PositionSide.SHORT,
        acquisition_date=datetime.date(2024, 2, 1),
        acquisition_cost=Decimal("50000.00"),
    )
    assert pos.status == PositionStatus.OPEN  # noqa: S101


def test_position_status_mutable() -> None:
    """Position status can be changed from OPEN to CLOSED."""
    pos = Position(
        id="pos-003",
        instrument_id="bond-003",
        book_type=BookType.BANKING,
        instrument_class=InstrumentClass.FVOCI,
        side=PositionSide.LONG,
        acquisition_date=datetime.date(2024, 3, 1),
        acquisition_cost=Decimal("75000.00"),
    )
    assert pos.status == PositionStatus.OPEN  # noqa: S101
    pos.status = PositionStatus.CLOSED
    assert pos.status == PositionStatus.CLOSED  # noqa: S101
