"""InterestIncomeAccrualRule: daily accrual for interest income on bonds and loans."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from brms.core.enums import PositionSide, TransactionType
from brms.core.models.transaction import Transaction

if TYPE_CHECKING:
    from brms.core.rules.context import RuleContext

_DAYS_PER_YEAR = Decimal("365")


class InterestIncomeAccrualRule:
    """Generate a daily INTEREST_ACCRUAL transaction for interest-bearing assets.

    Applies to LONG positions on instruments with a ``coupon_rate`` or
    ``interest_rate``.  The resulting transaction carries ``("side", "income")``
    metadata so the accounting service books:
    Dr Accrued Interest Receivable / Cr Interest Income.
    """

    def applies_to(
        self,
        instrument: object,
        position: object,
        _context: RuleContext,
    ) -> bool:
        """Return True if the instrument has an interest rate and position is LONG."""
        side = getattr(position, "side", None)
        if side != PositionSide.LONG:
            return False
        coupon_rate = getattr(instrument, "coupon_rate", None)
        interest_rate = getattr(instrument, "interest_rate", None)
        return coupon_rate is not None or interest_rate is not None

    def generate(
        self,
        instrument: object,
        position: object,
        context: RuleContext,
    ) -> list[Transaction]:
        """Generate a daily interest income accrual transaction."""
        rate = getattr(instrument, "coupon_rate", None) or getattr(instrument, "interest_rate", None)
        if rate is None:
            return []
        rate = Decimal(str(rate))

        # Use face_value for bonds, acquisition_cost for loans
        face_value = getattr(instrument, "face_value", None)
        if face_value is not None:
            notional = Decimal(str(face_value))
        else:
            notional = Decimal(str(getattr(position, "acquisition_cost", "0")))

        daily_interest = notional * rate / _DAYS_PER_YEAR
        if daily_interest == 0:
            return []

        return [
            Transaction(
                id=str(uuid.uuid4()),
                type=TransactionType.INTEREST_ACCRUAL,
                date=context.date,
                amount=daily_interest,
                position_id=getattr(position, "id", None),
                instrument_id=getattr(position, "instrument_id", None),
                metadata=(("side", "income"),),
            ),
        ]
