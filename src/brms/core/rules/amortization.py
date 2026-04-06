"""AmortizationRule: generates an amortization transaction on scheduled payment dates."""

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


class AmortizationRule:
    """Generates an AMORTIZATION transaction on each scheduled payment date."""

    def applies_to(
        self,
        instrument: object,
        _position: object,
        context: RuleContext,
    ) -> bool:
        """Return True if a payment date falls in the (previous_date, date] window.

        Supports instruments with a ``payment_schedule()`` method returning a tuple of
        three lists (interest, principal, outstanding), as well as instruments with a
        plain ``payment_dates`` attribute.
        """
        schedule = getattr(instrument, "payment_schedule", None)
        if callable(schedule):
            result = schedule()
            # Loans return (interest_pmt, principal_pmt, outstanding) tuple of 3 lists
            if isinstance(result, tuple) and len(result) == 3:  # noqa: PLR2004
                _interest_pmt, principal_pmt, _outstanding = result
                return any(_date_in_window(d, context) for d, _amount in principal_pmt)
        payment_dates = getattr(instrument, "payment_dates", None)
        if payment_dates is None:
            return False
        return any(_date_in_window(d, context) for d in payment_dates)

    def generate(
        self,
        instrument: object,
        position: object,
        context: RuleContext,
    ) -> list[Transaction]:
        """Generate an amortization transaction for the principal payment amount on this date."""
        amount = Decimal("0")

        schedule = getattr(instrument, "payment_schedule", None)
        if callable(schedule):
            result = schedule()
            if isinstance(result, tuple) and len(result) == 3:  # noqa: PLR2004
                _interest_pmt, principal_pmt, _outstanding = result
                for d, pmt_amount in principal_pmt:
                    if _date_in_window(d, context):
                        amount = Decimal(str(pmt_amount))
                        break

        if amount == 0:
            amount = Decimal(str(getattr(instrument, "periodic_payment", "0")))

        return [
            Transaction(
                id=str(uuid.uuid4()),
                type=TransactionType.AMORTIZATION,
                date=context.date,
                amount=amount,
                position_id=getattr(position, "id", None),
                instrument_id=getattr(position, "instrument_id", None),
            ),
        ]
