"""MaturityRule: generates a settlement transaction when an instrument reaches maturity."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from brms.core.models.transaction import Transaction, TransactionType

if TYPE_CHECKING:
    import datetime


class MaturityRule:
    """Generates a MATURITY_SETTLEMENT transaction on the instrument's maturity date."""

    def applies_to(
        self,
        instrument: object,
        _position: object,
        _market_state: object,
        date: datetime.date,
    ) -> bool:
        """Return True only on the exact maturity date of the instrument."""
        maturity = getattr(instrument, "maturity_date", None)
        return maturity is not None and maturity == date

    def generate(
        self,
        _instrument: object,
        position: object,
        _valuation_store: object,
        _market_state: object,
        date: datetime.date,
    ) -> list[Transaction]:
        """Generate a single maturity settlement transaction for the acquisition cost."""
        instrument_class = getattr(position, "instrument_class", None)
        instrument_class_name = instrument_class.name if instrument_class is not None else ""
        return [
            Transaction(
                id=str(uuid.uuid4()),
                type=TransactionType.MATURITY_SETTLEMENT,
                date=date,
                amount=Decimal(str(getattr(position, "acquisition_cost", "0"))),
                position_id=getattr(position, "id", None),
                instrument_id=getattr(position, "instrument_id", None),
                metadata=(("instrument_class", instrument_class_name),),
            ),
        ]
