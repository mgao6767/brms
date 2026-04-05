"""AmortizationRule: generates an amortization transaction on scheduled payment dates."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from brms.core.models.transaction import Transaction, TransactionType

if TYPE_CHECKING:
    import datetime


class AmortizationRule:
    """Generates an AMORTIZATION transaction on each scheduled payment date."""

    def applies_to(
        self,
        instrument: object,
        _position: object,
        _market_state: object,
        date: datetime.date,
    ) -> bool:
        """Return True if today is one of the instrument's payment dates."""
        payment_dates = getattr(instrument, "payment_dates", None)
        if payment_dates is None:
            return False
        return date in payment_dates

    def generate(
        self,
        instrument: object,
        _position: object,
        _valuation_store: object,
        _market_state: object,
        date: datetime.date,
    ) -> list[Transaction]:
        """Generate an amortization transaction using the instrument's periodic_payment amount."""
        periodic_payment = Decimal(str(getattr(instrument, "periodic_payment", "0")))
        return [
            Transaction(
                id=str(uuid.uuid4()),
                type=TransactionType.AMORTIZATION,
                date=date,
                amount=periodic_payment,
                instrument_id=getattr(instrument, "id", None),
            ),
        ]
