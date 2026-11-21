"""OperatingService: the day's operating expense, fee income and income tax for the whole bank.

These flows belong to no position. They are booked after the day's position transactions, so the
tax accrual sees the day's profit: tax to date = rate x max(0, pre-tax profit of the period), and
the day's tax is the change in that amount (a reversal when profit falls).
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from brms.core.models.accounting.accounts import AccountType
from brms.core.models.transaction import Transaction, TransactionType

if TYPE_CHECKING:
    import datetime

    from brms.core.models.bank import Bank

_DAYS = Decimal(365)
_CENT = Decimal("0.005")
_TAX_ACCOUNT = "Income Tax Expense"
_DIVIDENDS_ACCOUNT = "Dividends Paid"


def _tx(tx_type: TransactionType, amount: Decimal, date: datetime.date, description: str) -> Transaction:
    return Transaction(id=str(uuid.uuid4()), type=tx_type, date=date, amount=amount, description=description)


class OperatingService:
    """Stateless: reads the bank's operating inputs and the ledger, returns transactions."""

    def flows(self, bank: Bank, date: datetime.date) -> list[Transaction]:
        """Return the day's operating expense and non-interest income (before tax)."""
        config = bank.operating
        out = []
        if config.noninterest_expense:
            out.append(_tx(TransactionType.OPERATING_EXPENSE, config.noninterest_expense / _DAYS, date,
                           "Non-interest expense"))
        if config.noninterest_income:
            out.append(_tx(TransactionType.NONINTEREST_INCOME, config.noninterest_income / _DAYS, date,
                           "Non-interest income"))
        return out

    @staticmethod
    def _profit(bank: Bank) -> tuple[Decimal, Decimal]:
        """Return (pre-tax profit, income tax booked) of the period from the ledger."""
        pretax = Decimal(0)
        booked = Decimal(0)
        for account in bank.ledger.chart_of_accounts:
            if account.is_temporary_account or account.type not in (AccountType.INCOME, AccountType.EXPENSE):
                continue
            balance = Decimal(str(account.balance()))
            if account.name == _TAX_ACCOUNT:
                booked = balance
            elif account.type == AccountType.INCOME:
                pretax += balance
            else:
                pretax -= balance
        return pretax, booked

    def dividends(self, bank: Bank, date: datetime.date) -> list[Transaction]:
        """Return the day's dividend: payout x profit after tax to date, less what has been paid (never negative)."""
        payout = bank.operating.dividend_payout
        if payout == 0:
            return []
        pretax, tax = self._profit(bank)
        paid = Decimal(0)
        for account in bank.ledger.chart_of_accounts.all_accounts():
            if account.name == _DIVIDENDS_ACCOUNT:
                paid = Decimal(str(account.balance()))  # debit-normal contra account: positive when paid
        due = Decimal(str(payout)) * max(pretax - tax, Decimal(0)) - paid
        if due < _CENT:
            return []
        return [_tx(TransactionType.DIVIDEND, due, date, "Dividend")]

    def tax(self, bank: Bank, date: datetime.date) -> list[Transaction]:
        """Return the day's income tax: the change in rate x max(0, pre-tax profit of the period)."""
        rate = bank.operating.tax_rate
        if rate == 0:
            return []
        pretax, booked = self._profit(bank)
        change = Decimal(str(rate)) * max(pretax, Decimal(0)) - booked
        if abs(change) < _CENT:
            return []
        return [_tx(TransactionType.INCOME_TAX, change, date, "Income tax" if change > 0 else "Income tax reversal")]
