"""Position dataclass representing a financial position."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from brms.core.enums import BookType, InstrumentClass, PositionSide, PositionStatus

if TYPE_CHECKING:
    import datetime
    from decimal import Decimal


@dataclass
class Position:
    """Represents a financial position held by the bank."""

    id: str
    instrument_id: str
    book_type: BookType
    instrument_class: InstrumentClass
    side: PositionSide
    acquisition_date: datetime.date
    acquisition_cost: Decimal
    status: PositionStatus = field(default=PositionStatus.OPEN)
