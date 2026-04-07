"""InterestIncomeAccrualRule: accrues interest income on bonds and loans.

Uses the instrument's payment schedule (which has business-day-adjusted coupon
dates) to compute a daily accrual rate for the current coupon period.  Since
coupon dates are adjusted to business days, they always coincide with simulation
dates, eliminating period-boundary mismatch.

Accrual convention:
- Daily rate for a period = coupon_amount / calendar_days_in_period.
- Accrual range per advance: (previous_date, current_date].
- First advance (previous_date=None): starts from issue_date inclusive.
"""

from __future__ import annotations

import datetime
import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from brms.core.enums import PositionSide, TransactionType
from brms.core.models.transaction import Transaction

if TYPE_CHECKING:
    from brms.core.rules.context import RuleContext


class InterestIncomeAccrualRule:
    """Accrue interest income for LONG positions on coupon/interest-bearing instruments.

    Produces INTEREST_ACCRUAL transactions with ``("side", "income")`` metadata.
    Accounting: Dr Accrued Interest Receivable / Cr Interest Income.
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
        return (
            getattr(instrument, "coupon_rate", None) is not None
            or getattr(instrument, "interest_rate", None) is not None
        )

    def generate(
        self,
        instrument: object,
        position: object,
        context: RuleContext,
    ) -> list[Transaction]:
        """Generate an accrual transaction for the days since last advance."""
        accrual_start, accrual_end = self._accrual_range(instrument, position, context)
        calendar_days = (accrual_end - accrual_start).days
        if calendar_days <= 0:
            return []

        daily_rate = self._daily_rate(instrument, position, accrual_end)
        amount = daily_rate * calendar_days
        if amount == 0:
            return []

        return [
            Transaction(
                id=str(uuid.uuid4()),
                type=TransactionType.INTEREST_ACCRUAL,
                date=context.date,
                amount=amount,
                description=f"Interest income accrual ({calendar_days}d)",
                position_id=getattr(position, "id", None),
                instrument_id=getattr(position, "instrument_id", None),
                metadata=(("side", "income"),),
            ),
        ]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _accrual_range(
        instrument: object, position: object, context: RuleContext,
    ) -> tuple[datetime.date, datetime.date]:
        """Return (exclusive_start, inclusive_end) for this accrual step.

        Normal: (previous_date, date].
        First advance: (issue_date - 1day, date] so issue_date itself is included.
        """
        end = context.date
        if context.previous_date is not None:
            return context.previous_date, end

        # First advance: accrue from issue_date (exclusive) to date (inclusive).
        # Issue date is day 0 — no interest accrued yet. Interest starts day 1.
        issue_date = getattr(instrument, "issue_date", None)
        acq_date = getattr(position, "acquisition_date", None)
        return (issue_date or acq_date or end), end

    @staticmethod
    def _daily_rate(instrument: object, position: object, date: datetime.date) -> Decimal:
        """Compute daily accrual rate for the coupon period containing *date*.

        For QL-backed instruments with a payment_schedule: finds the period
        where period_start < date <= period_end, then returns
        coupon_amount / days_in_period.

        Falls back to face_value * rate / 365 for non-QL instruments.
        """
        schedule_fn = getattr(instrument, "payment_schedule", None)
        if callable(schedule_fn):
            payments = schedule_fn()
            if isinstance(payments, list) and payments:
                issue_date = getattr(instrument, "issue_date", None)
                prev_date = issue_date
                for pay_date, pay_amount in payments:
                    if isinstance(pay_date, datetime.date) and pay_date >= date:
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
        notional = Decimal(str(face_value)) if face_value else Decimal(str(getattr(position, "acquisition_cost", "0")))
        return notional * Decimal(str(rate)) / Decimal("365")
