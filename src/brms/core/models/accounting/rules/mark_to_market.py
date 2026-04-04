"""MarkToMarketRule: generates a mark-to-market transaction for FVTPL and FVOCI instruments."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from brms.core.models.instruments.base import InstrumentClass
from brms.core.models.transaction import Transaction, TransactionType

if TYPE_CHECKING:
    import datetime

_MTM_CLASSES = {InstrumentClass.FVTPL, InstrumentClass.FVOCI}


class MarkToMarketRule:
    """Generates a MARK_TO_MARKET transaction for instruments classified as FVTPL or FVOCI."""

    def applies_to(self, instrument: object, market_state: object, date: datetime.date) -> bool:  # noqa: ARG002
        """Return True if the instrument is classified as FVTPL or FVOCI."""
        instrument_class = getattr(instrument, "instrument_class", None)
        if instrument_class is None:
            return False
        return instrument_class in _MTM_CLASSES

    def generate(self, instrument: object, market_state: object, date: datetime.date) -> list[Transaction]:  # noqa: ARG002
        """Generate a mark-to-market transaction using face_value vs current value as a proxy for fair value change."""
        face_value = Decimal(str(getattr(instrument, "face_value", "0")))
        current_value = Decimal(str(getattr(instrument, "value", "0")))
        fair_value_change = current_value - face_value
        instrument_class: InstrumentClass = getattr(instrument, "instrument_class", InstrumentClass.NA)
        return [
            Transaction(
                id=str(uuid.uuid4()),
                type=TransactionType.MARK_TO_MARKET,
                date=date,
                amount=fair_value_change,
                instrument_id=getattr(instrument, "id", None),
                metadata=(("instrument_class", instrument_class.name),),
            ),
        ]
