"""AmortizationRule: generates an amortization transaction on scheduled payment dates."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from brms.core.models.transaction import Transaction, TransactionType

if TYPE_CHECKING:
    from brms.core.models.instruments.base import Instrument
    from brms.core.models.position import Position
    from brms.core.rules.context import RuleContext


class AmortizationRule:
    """Generates an AMORTIZATION transaction on each scheduled payment date."""

    def applies_to(
        self,
        instrument: Instrument,
        _position: Position,
        context: RuleContext,
    ) -> bool:
        """Return True if a payment date matches the current date exactly.

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
                return any(d == context.date for d, _amount in principal_pmt)
        payment_dates = getattr(instrument, "payment_dates", None)
        if payment_dates is None:
            return False
        return any(d == context.date for d in payment_dates)

    def generate(
        self,
        instrument: Instrument,
        position: Position,
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
                    if d == context.date:
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
