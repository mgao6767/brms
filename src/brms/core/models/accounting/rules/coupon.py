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

    def applies_to(
        self,
        instrument: object,
        _position: object,
        _market_state: object,
        date: datetime.date,
    ) -> bool:
        """Return True if today is one of the instrument's coupon payment dates.

        Supports QL-backed bonds with a ``payment_schedule()`` method returning
        ``(date, amount)`` tuples, as well as instruments with a plain
        ``coupon_dates`` attribute.
        """
        schedule = getattr(instrument, "payment_schedule", None)
        if callable(schedule):
            result = schedule()
            # Bonds return list[(date, amount)]; loans return tuple of 3 lists
            if isinstance(result, list):
                return any(d == date for d, _amount in result)
        coupon_dates = getattr(instrument, "coupon_dates", [])
        return date in coupon_dates

    def generate(
        self,
        instrument: object,
        position: object,
        _valuation_store: object,
        _market_state: object,
        date: datetime.date,
    ) -> list[Transaction]:
        """Generate a coupon payment transaction using the instrument's payment schedule or terms."""
        coupon_amount: Decimal | None = None

        # Try QL-backed payment schedule first (bonds return list[(date, amount)])
        schedule = getattr(instrument, "payment_schedule", None)
        if callable(schedule):
            result = schedule()
            if isinstance(result, list):
                for d, amount in result:
                    if d == date:
                        coupon_amount = Decimal(str(amount))
                        break

        # Fall back to explicit coupon_amount or compute from terms
        if coupon_amount is None:
            explicit = getattr(instrument, "coupon_amount", None)
            if explicit is not None:
                coupon_amount = Decimal(str(explicit))
            else:
                face_value = Decimal(str(getattr(instrument, "face_value", "0")))
                coupon_rate = Decimal(str(getattr(instrument, "coupon_rate", "0")))
                coupon_amount = face_value * coupon_rate

        return [
            Transaction(
                id=str(uuid.uuid4()),
                type=TransactionType.COUPON_PAYMENT,
                date=date,
                amount=coupon_amount,
                position_id=getattr(position, "id", None),
                instrument_id=getattr(position, "instrument_id", None),
            ),
        ]
