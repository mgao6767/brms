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
        """Return True if today is one of the instrument's payment dates.

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
                return any(d == date for d, _amount in principal_pmt)
        payment_dates = getattr(instrument, "payment_dates", None)
        if payment_dates is None:
            return False
        return date in payment_dates

    def generate(
        self,
        instrument: object,
        position: object,
        _valuation_store: object,
        _market_state: object,
        date: datetime.date,
    ) -> list[Transaction]:
        """Generate an amortization transaction for the principal payment amount on this date."""
        amount = Decimal("0")

        schedule = getattr(instrument, "payment_schedule", None)
        if callable(schedule):
            result = schedule()
            if isinstance(result, tuple) and len(result) == 3:  # noqa: PLR2004
                _interest_pmt, principal_pmt, _outstanding = result
                for d, pmt_amount in principal_pmt:
                    if d == date:
                        amount = Decimal(str(pmt_amount))
                        break

        if amount == 0:
            amount = Decimal(str(getattr(instrument, "periodic_payment", "0")))

        return [
            Transaction(
                id=str(uuid.uuid4()),
                type=TransactionType.AMORTIZATION,
                date=date,
                amount=amount,
                position_id=getattr(position, "id", None),
                instrument_id=getattr(position, "instrument_id", None),
            ),
        ]
