"""InterestPaymentRule: generates a semi-annual coupon payment transaction on scheduled coupon dates."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from brms.core.models.transaction import Transaction, TransactionType

if TYPE_CHECKING:
    import datetime


class InterestPaymentRule:
    """Generates a COUPON_PAYMENT transaction on each scheduled coupon date using semi-annual convention."""

    def applies_to(
        self,
        instrument: object,
        _position: object,
        _market_state: object,
        date: datetime.date,
    ) -> bool:
        """Return True if today is one of the instrument's coupon payment dates."""
        coupon_dates = getattr(instrument, "coupon_dates", None)
        if coupon_dates is None:
            return False
        return date in coupon_dates

    def generate(
        self,
        instrument: object,
        _position: object,
        _valuation_store: object,
        _market_state: object,
        date: datetime.date,
    ) -> list[Transaction]:
        """Generate a semi-annual coupon payment transaction (face_value * coupon_rate / 2)."""
        face_value = Decimal(str(getattr(instrument, "face_value", "0")))
        coupon_rate = Decimal(str(getattr(instrument, "coupon_rate", "0")))
        amount = face_value * coupon_rate / Decimal("2")
        return [
            Transaction(
                id=str(uuid.uuid4()),
                type=TransactionType.COUPON_PAYMENT,
                date=date,
                amount=amount,
                instrument_id=getattr(instrument, "id", None),
            ),
        ]
