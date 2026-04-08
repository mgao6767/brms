"""InterestPaymentRule: generates interest payment transactions on scheduled payment dates."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from brms.core.models.transaction import Transaction, TransactionType

if TYPE_CHECKING:
    import datetime

    from brms.core.models.instruments.base import Instrument
    from brms.core.models.position import Position
    from brms.core.rules.context import RuleContext


def _date_in_window(d: datetime.date, context: RuleContext) -> bool:
    """Return True if date *d* falls in the half-open window (previous_date, date].

    When there is no previous_date (first simulation day), only exact match counts.
    """
    if context.previous_date is not None:
        return context.previous_date < d <= context.date  # type: ignore[operator]
    return d == context.date


class InterestPaymentRule:
    """Generates a COUPON_PAYMENT transaction on each scheduled coupon date using instrument terms."""

    def applies_to(
        self,
        instrument: Instrument,
        _position: Position,
        context: RuleContext,
    ) -> bool:
        """Return True if a payment date falls in the (previous_date, date] window.

        Supports instruments with a ``payment_schedule()`` method returning
        ``(date, amount)`` tuples or a tuple of 3 lists, as well as instruments
        with a plain ``coupon_dates`` attribute.
        """
        # Try QL-backed payment schedule first
        schedule = getattr(instrument, "payment_schedule", None)
        if callable(schedule):
            result = schedule()
            if isinstance(result, list):
                return any(_date_in_window(d, context) for d, _amount in result)
            # Loans return (interest_pmt, principal_pmt, outstanding) tuple of 3 lists
            if isinstance(result, tuple) and len(result) == 3:  # noqa: PLR2004
                interest_pmt, _principal_pmt, _outstanding = result
                return any(_date_in_window(d, context) for d, _amount in interest_pmt)

        coupon_dates = getattr(instrument, "coupon_dates", None)
        if coupon_dates is None:
            return False
        return any(_date_in_window(d, context) for d in coupon_dates)

    def generate(
        self,
        instrument: Instrument,
        position: Position,
        context: RuleContext,
    ) -> list[Transaction]:
        """Generate an interest payment transaction (face_value * coupon_rate / 2)."""
        face_value = Decimal(str(getattr(instrument, "face_value", "0")))
        coupon_rate = Decimal(str(getattr(instrument, "coupon_rate", "0")))
        amount = face_value * coupon_rate / Decimal("2")
        return [
            Transaction(
                id=str(uuid.uuid4()),
                type=TransactionType.COUPON_PAYMENT,
                date=context.date,
                amount=amount,
                position_id=getattr(position, "id", None),
                instrument_id=getattr(position, "instrument_id", None),
            ),
        ]
