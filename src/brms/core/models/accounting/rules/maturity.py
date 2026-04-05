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
        instrument: object,
        _position: object,
        _valuation_store: object,
        _market_state: object,
        date: datetime.date,
    ) -> list[Transaction]:
        """Generate a single maturity settlement transaction for the face value."""
        return [
            Transaction(
                id=str(uuid.uuid4()),
                type=TransactionType.MATURITY_SETTLEMENT,
                date=date,
                amount=Decimal(str(getattr(instrument, "face_value", "0"))),
                instrument_id=getattr(instrument, "id", None),
            ),
        ]
