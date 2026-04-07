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
        """Generate an interest income accrual transaction.

        For instruments with a payment_schedule (QL-backed bonds), the daily
        accrual rate is derived from the current coupon period so that the
        total accrued exactly matches the coupon payment at settlement.

        For other instruments, falls back to face_value * rate / 365.
        """
        # Cover all calendar days since last advance (weekends/holidays).
        # On the first advance (previous_date=None), accrue from period start
        # (issue_date or last coupon date) so we don't miss the gap before
        # the simulation started.
        if context.previous_date is not None:
            calendar_days = (context.date - context.previous_date).days
        else:
            # First advance: accrue from the start of the current coupon period
            issue_date = getattr(instrument, "issue_date", None)
            acq_date = getattr(position, "acquisition_date", None)
            period_start = issue_date or acq_date
            if period_start is not None:
                # +1 to include the start day (e.g., Jan 1 to Jan 3 = 3 days inclusive)
                calendar_days = (context.date - period_start).days + 1
            else:
                calendar_days = 1
            if calendar_days <= 0:
                calendar_days = 1

        daily_rate = self._daily_rate_for_period(instrument, position, context.date)
        amount = daily_rate * calendar_days
        if amount == 0:
            return []

        return [
            Transaction(
                id=str(uuid.uuid4()),
                type=TransactionType.INTEREST_ACCRUAL,
                date=context.date,
                amount=amount,
                position_id=getattr(position, "id", None),
                instrument_id=getattr(position, "instrument_id", None),
                description=f"Interest income accrual ({calendar_days}d)",
                metadata=(("side", "income"),),
            ),
        ]

    @staticmethod
    def _daily_rate_for_period(instrument: object, position: object, date: object) -> Decimal:
        """Compute the daily accrual rate for the current coupon period.

        For bonds with payment_schedule: coupon_amount / days_in_period.
        This ensures total accrual over the period exactly equals the coupon.
        """
        import datetime

        schedule = getattr(instrument, "payment_schedule", None)
        if callable(schedule):
            payments = schedule()
            if isinstance(payments, list) and payments:
                # Find the coupon period containing `date`.
                # For the first period, use the issue date as the start.
                issue_date = getattr(instrument, "issue_date", None)
                prev_date = issue_date
                for pay_date, pay_amount in payments:
                    if isinstance(pay_date, datetime.date) and pay_date > date:
                        if prev_date is not None:
                            days_in_period = (pay_date - prev_date).days
                            if days_in_period > 0:
                                return Decimal(str(pay_amount)) / Decimal(str(days_in_period))
                        break
                    prev_date = pay_date

        # Fallback: simple rate / 365
        rate = getattr(instrument, "coupon_rate", None) or getattr(instrument, "interest_rate", None)
        if rate is None:
            return Decimal("0")
        face_value = getattr(instrument, "face_value", None)
        if face_value is not None:
            notional = Decimal(str(face_value))
        else:
            notional = Decimal(str(getattr(position, "acquisition_cost", "0")))
        return notional * Decimal(str(rate)) / _DAYS_PER_YEAR
