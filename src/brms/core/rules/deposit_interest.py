"""Deposit rules: daily interest accrual, monthly settlement, and balance flows.

All amounts come from the deposit's valuation records: ``CARRYING_VALUE`` is the balance and
``ACCRUED_INTEREST`` the interest payable since the last settlement (the 1st of each month).
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from brms.core.enums import InterestSide, TransactionType, TxMeta, ValuationType
from brms.core.exceptions import ValuationError
from brms.core.models.transaction import Transaction

if TYPE_CHECKING:
    import datetime

    from brms.core.models.instruments.base import Instrument
    from brms.core.models.position import Position
    from brms.core.rules.context import RuleContext


def is_settlement_day(date: datetime.date) -> bool:
    """Deposit interest is paid on the first calendar day of each month."""
    return date.day == 1


def _value(context: RuleContext, position: Position, vtype: ValuationType, *, previous: bool = False) -> Decimal:
    store = context.valuation_store
    if previous:
        value = store.get_previous(position.id, context.date, vtype)
    else:
        value = store.get(position.id, context.date, vtype)
    if value is None:
        when = "before" if previous else "on"
        msg = f"Deposit position {position.id} has no {vtype.name} {when} {context.date}"
        raise ValuationError(msg)
    return Decimal(value)


def _tx(  # noqa: PLR0913
    tx_type: TransactionType,
    amount: Decimal,
    position: Position,
    context: RuleContext,
    description: str,
    *,
    side: bool = True,
) -> list[Transaction]:
    if amount == 0:
        return []
    metadata = ((TxMeta.SIDE, InterestSide.EXPENSE),) if side else ()
    return [Transaction(
        id=str(uuid.uuid4()), type=tx_type, date=context.date, amount=amount, position_id=position.id,
        instrument_id=position.instrument_id, description=description, metadata=metadata,
    )]


class DepositInterestAccrualRule:
    """Accrue the day's deposit interest: Dr Interest Expense / Cr Interest Payable."""

    def applies_to(self, _instrument: Instrument, _position: Position, _context: RuleContext) -> bool:
        """Run every day."""
        return True

    def generate(self, _instrument: Instrument, position: Position, context: RuleContext) -> list[Transaction]:
        """Accrue the change in interest payable (all of it on a settlement day)."""
        payable = _value(context, position, ValuationType.ACCRUED_INTEREST)
        if not is_settlement_day(context.date):
            payable -= _value(context, position, ValuationType.ACCRUED_INTEREST, previous=True)
        return _tx(TransactionType.INTEREST_ACCRUAL, payable, position, context, "Deposit interest accrual")


class DepositInterestSettlementRule:
    """Pay the interest accrued to the end of the previous day: Dr Interest Payable / Cr Cash."""

    def applies_to(self, _instrument: Instrument, _position: Position, context: RuleContext) -> bool:
        """Return True on the first day of each month."""
        return context.previous_date is not None and is_settlement_day(context.date)

    def generate(self, _instrument: Instrument, position: Position, context: RuleContext) -> list[Transaction]:
        """Settle the previous day's interest payable."""
        payable = _value(context, position, ValuationType.ACCRUED_INTEREST, previous=True)
        return _tx(TransactionType.INTEREST_SETTLEMENT, payable, position, context, "Monthly deposit interest")


class DepositFlowRule:
    """Move cash for the day's change in balance: withdrawals (run-off, scheduled) or inflows."""

    def applies_to(self, _instrument: Instrument, _position: Position, _context: RuleContext) -> bool:
        """Run every day."""
        return True

    def generate(self, _instrument: Instrument, position: Position, context: RuleContext) -> list[Transaction]:
        """Emit DEPOSIT_WITHDRAWAL for a fall in balance, DEPOSIT_RECEIVED for a rise."""
        change = _value(context, position, ValuationType.CARRYING_VALUE)
        change -= _value(context, position, ValuationType.CARRYING_VALUE, previous=True)
        if change < 0:
            return _tx(TransactionType.DEPOSIT_WITHDRAWAL, -change, position, context, "Deposit outflow", side=False)
        return _tx(TransactionType.DEPOSIT_RECEIVED, change, position, context, "Deposit inflow", side=False)
