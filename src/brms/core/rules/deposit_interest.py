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
        """Generate a daily interest accrual transaction for the deposit."""
        acquisition_cost = Decimal(str(getattr(position, "acquisition_cost", "0")))
        daily_interest = acquisition_cost * self._annual_rate / _DAYS_PER_YEAR
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
        """Generate a monthly interest settlement transaction."""
        acquisition_cost = Decimal(str(getattr(position, "acquisition_cost", "0")))
        amount = acquisition_cost * self._annual_rate / Decimal("12")
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
