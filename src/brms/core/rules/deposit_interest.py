"""Deposit interest rules: daily accrual and monthly settlement."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from brms.core.enums import InstrumentType, TransactionType
from brms.core.models.transaction import Transaction

if TYPE_CHECKING:
    from brms.core.rules.context import RuleContext

_DEFAULT_ANNUAL_RATE = Decimal("0.02")
_DAYS_PER_YEAR = Decimal("365")


class DepositInterestAccrualRule:
    """Generate a daily INTEREST_ACCRUAL transaction for deposit positions.

    Banks pay interest on customer deposits.  This rule computes a simplified
    daily accrual using a fixed annual rate (default 2 %) divided by 365.
    The resulting transaction carries ``("side", "expense")`` metadata so the
    accounting service books:  Dr Interest Expense / Cr Interest Payable.
    """

    def __init__(self, annual_rate: Decimal = _DEFAULT_ANNUAL_RATE) -> None:
        """Initialise the rule with the given annual interest rate."""
        self._annual_rate = annual_rate

    def applies_to(
        self,
        instrument: object,
        _position: object,
        _context: RuleContext,
    ) -> bool:
        """Return True if the instrument is a deposit."""
        instrument_type = getattr(instrument, "instrument_type", None)
        return instrument_type == InstrumentType.DEPOSIT

    def generate(
        self,
        _instrument: object,
        position: object,
        context: RuleContext,
    ) -> list[Transaction]:
        """Generate an interest accrual transaction covering all calendar days since last advance.

        When the simulation skips weekends/holidays (e.g., Friday → Monday),
        the accrual covers all skipped calendar days so that the total accrued
        over a month matches the calendar-based settlement amount.
        """
        acquisition_cost = Decimal(str(getattr(position, "acquisition_cost", "0")))
        daily_rate = acquisition_cost * self._annual_rate / _DAYS_PER_YEAR

        # Number of calendar days since last advance (covers weekends/holidays)
        if context.previous_date is not None:
            calendar_days = (context.date - context.previous_date).days
        else:
            calendar_days = 1

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
                metadata=(("side", "expense"),),
            ),
        ]


class DepositInterestSettlementRule:
    """Monthly settlement of accrued deposit interest.

    Fires on the first business day of each month (when previous_date's month
    differs from current date's month).  Generates an INTEREST_SETTLEMENT
    transaction with ``("side", "expense")`` metadata so the accounting service
    books:  Dr Interest Payable / Cr Cash.
    """

    def __init__(self, annual_rate: Decimal = _DEFAULT_ANNUAL_RATE) -> None:
        """Initialise the rule with the given annual interest rate."""
        self._annual_rate = annual_rate

    def applies_to(
        self,
        instrument: object,
        _position: object,
        context: RuleContext,
    ) -> bool:
        """Return True on the first day of a new month for deposit instruments."""
        instrument_type = getattr(instrument, "instrument_type", None)
        if instrument_type != InstrumentType.DEPOSIT:
            return False
        if context.previous_date is None:
            return False
        return context.previous_date.month != context.date.month

    def generate(
        self,
        _instrument: object,
        position: object,
        context: RuleContext,
    ) -> list[Transaction]:
        """Settle accrued interest for the previous month.

        Computes the number of calendar days that were actually accrued in the
        previous month.  For the first month, starts from acquisition_date
        instead of the 1st to match the accrual rule.
        """
        import datetime

        acquisition_cost = Decimal(str(getattr(position, "acquisition_cost", "0")))
        prev = context.previous_date
        acq_date = getattr(position, "acquisition_date", None)

        # Start of accrual period: 1st of previous month, or acquisition date if later
        month_start = datetime.date(prev.year, prev.month, 1)
        if acq_date is not None and acq_date > month_start:
            period_start = acq_date
        else:
            period_start = month_start

        # End of accrual period: last day of previous month (= previous_date since month just changed)
        period_end = prev

        days = (period_end - period_start).days + 1
        if days <= 0:
            return []
        amount = acquisition_cost * self._annual_rate * days / _DAYS_PER_YEAR
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
                metadata=(("side", "expense"),),
            ),
        ]
