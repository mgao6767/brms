"""CouponPaymentRule: generates a coupon payment transaction on scheduled coupon dates."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from brms.core.models.transaction import Transaction, TransactionType

if TYPE_CHECKING:
    from brms.core.rules.context import RuleContext


def _date_in_window(d: object, context: RuleContext) -> bool:
    """Return True if date *d* falls in the half-open window (previous_date, date].

    When there is no previous_date (first simulation day), only exact match counts.
    """
    if context.previous_date is not None:
        return context.previous_date < d <= context.date  # type: ignore[operator]
    return d == context.date


class CouponPaymentRule:
    """Generates a COUPON_PAYMENT transaction on each scheduled coupon date."""

    def applies_to(
        self,
        instrument: object,
        _position: object,
        context: RuleContext,
    ) -> bool:
        """Return True if a coupon date falls in the (previous_date, date] window.

        Supports QL-backed bonds with a ``payment_schedule()`` method returning
        ``(date, amount)`` tuples, as well as instruments with a plain
        ``coupon_dates`` attribute.
        """
        schedule = getattr(instrument, "payment_schedule", None)
        if callable(schedule):
            result = schedule()
            # Bonds return list[(date, amount)]; loans return tuple of 3 lists
            if isinstance(result, list):
                return any(_date_in_window(d, context) for d, _amount in result)
        coupon_dates = getattr(instrument, "coupon_dates", [])
        return any(_date_in_window(d, context) for d in coupon_dates)

    def generate(
        self,
        instrument: object,
        position: object,
        context: RuleContext,
    ) -> list[Transaction]:
        """Generate a coupon payment transaction using the instrument's payment schedule or terms."""
        coupon_amount: Decimal | None = None

        # Try QL-backed payment schedule first (bonds return list[(date, amount)])
        schedule = getattr(instrument, "payment_schedule", None)
        if callable(schedule):
            result = schedule()
            if isinstance(result, list):
                for d, amount in result:
                    if _date_in_window(d, context):
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
                type=TransactionType.INTEREST_SETTLEMENT,
                date=context.date,
                amount=coupon_amount,
                position_id=getattr(position, "id", None),
                instrument_id=getattr(position, "instrument_id", None),
                metadata=(("side", "income"),),
            ),
        ]
