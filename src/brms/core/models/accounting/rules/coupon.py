"""CouponPaymentRule: generates a coupon payment transaction on scheduled coupon dates."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from brms.core.models.transaction import Transaction, TransactionType

if TYPE_CHECKING:
    import datetime


class CouponPaymentRule:
    """Generates a COUPON_PAYMENT transaction on each scheduled coupon date."""

    def applies_to(self, instrument: object, market_state: object, date: datetime.date) -> bool:  # noqa: ARG002
        """Return True if today is one of the instrument's coupon payment dates."""
        coupon_dates = getattr(instrument, "coupon_dates", [])
        return date in coupon_dates

    def generate(self, instrument: object, market_state: object, date: datetime.date) -> list[Transaction]:  # noqa: ARG002
        """Generate a coupon payment transaction using the instrument's coupon amount."""
        coupon_amount = getattr(instrument, "coupon_amount", None)
        if coupon_amount is None:
            face_value = Decimal(str(getattr(instrument, "face_value", "0")))
            coupon_rate = Decimal(str(getattr(instrument, "coupon_rate", "0")))
            coupon_amount = face_value * coupon_rate
        return [
            Transaction(
                id=str(uuid.uuid4()),
                type=TransactionType.COUPON_PAYMENT,
                date=date,
                amount=Decimal(str(coupon_amount)),
                instrument_id=getattr(instrument, "id", None),
            ),
        ]
