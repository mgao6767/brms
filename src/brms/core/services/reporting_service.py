"""ReportingService — pure computation of financial statements from a Ledger.

The balance sheet is produced "as if closed" on the reporting date: a deep copy
of the ledger is closed so that income and expenses are transferred to Retained
Earnings.  The original ledger is never modified.
"""

from __future__ import annotations

import copy
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import datetime

    from brms.core.models.accounting.accounts import TAccount
    from brms.core.models.accounting.ledger import Ledger

from brms.core.enums import EntryKind
from brms.core.models.accounting.accounts import AccountNormalBalance, AccountType


class ReportingService:
    """Generate structured financial statement data from a Ledger.

    All methods are pure computations — no HTML, no UI concerns.
    """

    def trial_balance(self, ledger: Ledger) -> list[dict[str, Any]]:
        """Return a trial balance for all accounts in the ledger.

        Each row is a dict with keys: account, debit, credit, balance.
        """
        return [
            {
                "account": account.name,
                "debit": account.debit_value,
                "credit": account.credit_value,
                "balance": account.balance(),
            }
            for account in ledger.chart_of_accounts
        ]

    def balance_sheet(
        self, ledger: Ledger, date: datetime.date | None = None,
    ) -> dict[str, Any]:
        """Return a structured balance sheet, closed as of *date*.

        A deep copy of the ledger is closed so that all income and expense
        balances are transferred to Retained Earnings.  The result is a clean
        balance sheet with only permanent accounts (Assets, Liabilities, Equity).
        The original ledger is not modified.
        """
        # Close a copy so the live ledger is untouched
        closed = copy.deepcopy(ledger)
        if date is not None:
            closed.close_ledger(date)

        assets: list[dict[str, Any]] = []
        liabilities: list[dict[str, Any]] = []
        equity: list[dict[str, Any]] = []

        for account in closed.chart_of_accounts:
            # Skip temporary accounts (Income Summary) — they're zeroed after closing
            if account.is_temporary_account:
                continue
            entry = {"account": account.name, "balance": account.balance()}
            if account.type == AccountType.ASSET:
                assets.append(entry)
            elif account.type == AccountType.LIABILITY:
                liabilities.append(entry)
            elif account.type == AccountType.EQUITY:
                equity.append(entry)

        total_assets = sum(row["balance"] for row in assets)
        total_liabilities = sum(row["balance"] for row in liabilities)
        total_equity = sum(row["balance"] for row in equity)

        return {
            "assets": assets,
            "liabilities": liabilities,
            "equity": equity,
            "total_assets": total_assets,
            "total_liabilities": total_liabilities,
            "total_equity": total_equity,
        }

    def income_statement(
        self,
        ledger: Ledger,
        start: datetime.date | None = None,
        end: datetime.date | None = None,
    ) -> dict[str, Any]:
        """Return a structured income statement.

        Without a window, shows the current income and expense account balances (profit
        since the books were last closed). With *start* and/or *end*, shows the profit and
        loss posted by ordinary journal entries dated within ``[start, end]``; opening and
        closing entries are excluded.
        """
        windowed = start is not None or end is not None
        movements = self._movements(ledger, start, end) if windowed else {}
        income: list[dict[str, Any]] = []
        expenses: list[dict[str, Any]] = []

        for account in ledger.chart_of_accounts:
            if account.is_temporary_account:
                continue
            if account.type not in (AccountType.INCOME, AccountType.EXPENSE):
                continue
            balance = self._window_balance(account, movements) if windowed else account.balance()
            entry = {"account": account.name, "balance": balance}
            (income if account.type == AccountType.INCOME else expenses).append(entry)

        total_income = sum(row["balance"] for row in income)
        total_expenses = sum(row["balance"] for row in expenses)
        net_income = total_income - total_expenses

        return {
            "income": income,
            "expenses": expenses,
            "total_income": total_income,
            "total_expenses": total_expenses,
            "net_income": net_income,
        }

    @staticmethod
    def _movements(
        ledger: Ledger, start: datetime.date | None, end: datetime.date | None,
    ) -> dict[int, tuple[float, float]]:
        """Return {id(account): (debits, credits)} posted by NORMAL entries within the window."""
        totals: dict[int, tuple[float, float]] = {}
        for entry in ledger.journal.entries:
            if entry.kind != EntryKind.NORMAL or entry.date is None:
                continue
            if (start is not None and entry.date < start) or (end is not None and entry.date > end):
                continue
            for account, value in entry.debit_account_value_pairs():
                debit, credit = totals.get(id(account), (0.0, 0.0))
                totals[id(account)] = (debit + value, credit)
            for account, value in entry.credit_account_value_pairs():
                debit, credit = totals.get(id(account), (0.0, 0.0))
                totals[id(account)] = (debit, credit + value)
        return totals

    @staticmethod
    def _window_balance(account: TAccount, movements: dict[int, tuple[float, float]]) -> float:
        """Net window movement of *account* (summed over its posting leaves) in its normal direction."""
        debits = credits_ = 0.0
        for leaf in account.posting_accounts():
            debit, credit = movements.get(id(leaf), (0.0, 0.0))
            debits += debit
            credits_ += credit
        if account.normal_balance == AccountNormalBalance.DEBIT_NORMAL:
            return debits - credits_
        return credits_ - debits
