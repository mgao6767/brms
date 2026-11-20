"""Deposit interest rules: daily accrual and monthly settlement."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from brms.core.enums import InterestSide, TransactionType, TxMeta
from brms.core.exceptions import UnsupportedPositionError
from brms.core.models.transaction import Transaction

if TYPE_CHECKING:
    from brms.core.models.instruments.base import Instrument
    from brms.core.models.position import Position
    from brms.core.rules.context import RuleContext

_DAYS_PER_YEAR = Decimal("365")


def _deposit_rate(instrument: Instrument, position: Position) -> Decimal:
    """Return the deposit's interest rate; a deposit without one is an input error."""
    rate = getattr(instrument, "interest_rate", None)
    if rate is None:
        msg = f"Deposit position {position.id} has no interest rate"
        raise UnsupportedPositionError(msg)
    return Decimal(str(rate))


class DepositInterestAccrualRule:
    """Generate a daily INTEREST_ACCRUAL transaction for deposit positions.

    Banks pay interest on customer deposits.  This rule computes a simplified
    daily accrual using a fixed annual rate (default 2 %) divided by 365.
    The resulting transaction carries ``("side", "expense")`` metadata so the
    accounting service books:  Dr Interest Expense / Cr Interest Payable.
    """

    @staticmethod
    def _rate_for(instrument: Instrument, position: Position) -> Decimal:
        return _deposit_rate(instrument, position)

    def applies_to(
        self,
        _instrument: Instrument,
        _position: Position,
        _context: RuleContext,
    ) -> bool:
        """Return True unconditionally — runs every simulation day."""
        return True

    def generate(
        self,
        instrument: Instrument,
        position: Position,
        context: RuleContext,
    ) -> list[Transaction]:
        """Generate a 1-day interest accrual transaction.

        Since the simulation advances one calendar day at a time, the accrual
        is always exactly ``cost * rate / 365``.
        """
        acquisition_cost = Decimal(str(getattr(position, "acquisition_cost", "0")))
        rate = self._rate_for(instrument, position)
        if rate == 0:
            return []
        amount = acquisition_cost * rate / _DAYS_PER_YEAR

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
                description="Deposit interest accrual (1d)",
                metadata=((TxMeta.SIDE, InterestSide.EXPENSE),),
            ),
        ]


class DepositInterestSettlementRule:
    """Monthly settlement of accrued deposit interest.

    Fires on the first business day of each month (when previous_date's month
    differs from current date's month).  Generates an INTEREST_SETTLEMENT
    transaction with ``("side", "expense")`` metadata so the accounting service
    books:  Dr Interest Payable / Cr Cash.
    """

    @staticmethod
    def _rate_for(instrument: Instrument, position: Position) -> Decimal:
        return _deposit_rate(instrument, position)

    def applies_to(
        self,
        _instrument: Instrument,
        _position: Position,
        context: RuleContext,
    ) -> bool:
        """Return True on the 1st of each month (timing check only)."""
        if context.previous_date is None:
            return False
        return context.date.day == 1

    def generate(
        self,
        instrument: Instrument,
        position: Position,
        context: RuleContext,
    ) -> list[Transaction]:
        """Settle accrued interest for the previous month.

        Uses ``calendar.monthrange`` to determine the number of days in the
        previous month.  For the first month, starts from acquisition_date
        instead of the 1st to match the accrual rule.
        """
        import calendar

        rate = self._rate_for(instrument, position)
        if rate == 0:
            return []

        acquisition_cost = Decimal(str(getattr(position, "acquisition_cost", "0")))
        prev = context.previous_date
        acq_date = getattr(position, "acquisition_date", None)

        # Skip if the deposit didn't exist during the previous month
        if acq_date is not None and acq_date > prev:
            return []

        # Number of days in previous month
        _, month_days = calendar.monthrange(prev.year, prev.month)

        if acq_date is not None and acq_date.year == prev.year and acq_date.month == prev.month:
            # Acquired at close of business: interest accrues from the following day.
            days = month_days - acq_date.day
        else:
            days = month_days

        if days <= 0:
            return []
        amount = acquisition_cost * rate * days / _DAYS_PER_YEAR
        if amount == 0:
            return []
        return [
            Transaction(
                id=str(uuid.uuid4()),
                type=TransactionType.INTEREST_SETTLEMENT,
                date=context.date,
                amount=amount,
                position_id=getattr(position, "id", None),
                instrument_id=getattr(position, "instrument_id", None),
                description=f"Monthly deposit interest settlement ({days}d)",
                metadata=((TxMeta.SIDE, InterestSide.EXPENSE),),
            ),
        ]
