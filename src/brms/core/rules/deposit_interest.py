"""DepositInterestRule: generates daily interest expense for deposit positions."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from brms.core.enums import InstrumentType
from brms.core.models.transaction import Transaction, TransactionType

if TYPE_CHECKING:
    from brms.core.rules.context import RuleContext

_DEFAULT_ANNUAL_RATE = Decimal("0.02")
_DAYS_PER_YEAR = Decimal("365")


class DepositInterestRule:
    """Generates a daily INTEREST_EXPENSE transaction for deposit positions.

    Banks pay interest on customer deposits.  This rule computes a simplified
    daily accrual using a fixed annual rate (default 2%) divided by 365.
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
        """Generate a daily interest expense transaction for the deposit."""
        acquisition_cost = Decimal(str(getattr(position, "acquisition_cost", "0")))
        daily_interest = acquisition_cost * self._annual_rate / _DAYS_PER_YEAR
        if daily_interest == 0:
            return []
        return [
            Transaction(
                id=str(uuid.uuid4()),
                type=TransactionType.INTEREST_EXPENSE,
                date=context.date,
                amount=daily_interest,
                position_id=getattr(position, "id", None),
                instrument_id=getattr(position, "instrument_id", None),
            ),
        ]
