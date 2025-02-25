"""Module for financial statements and reports."""

import datetime
from abc import ABC, abstractmethod
from collections import UserDict
from copy import deepcopy
from dataclasses import dataclass
from typing import TYPE_CHECKING

from brms.accounting.account import (
    AccountBalances,
    AccountNormalBalance,
    AccountType,
    AccumulatedOCIAccount,
    EquityAccount,
    RetainedEarningsAccount,
)

if TYPE_CHECKING:
    from brms.accounting.account import TAccount
    from brms.accounting.ledger import Ledger
    from brms.accounting.statement_viewer import StatementVisitor


class Statement(ABC):
    """Abstract base class for statements."""

    name: str
    date: datetime.date | None = None
    html: str = ""
    text: str = ""

    @classmethod
    @abstractmethod
    def from_ledger(cls, ledger: "Ledger") -> "Statement":
        """Create a statement from the given ledger."""

    @abstractmethod
    def accept(self, visitor: "StatementVisitor") -> str:
        """Accept a StatementVisitor to generate a view of the statement."""


class TrialBalance(UserDict["TAccount", tuple[float, float]], Statement):
    """Class representing a trial balance."""

    name = "Trial Balance"

    @classmethod
    def from_ledger(cls, ledger: "Ledger") -> "TrialBalance":
        """Create a TrialBalance from the given ledger."""
        trial_balance = cls()
        trial_balance.date = ledger.date_closed
        for account in ledger.get_account_balances():
            trial_balance[account] = cls.get_credit_and_debit_values(account)
        return trial_balance

    def accept(self, visitor: "StatementVisitor") -> str:
        """Accept a StatementVisitor to generate a view of the statement."""
        return visitor.visit_trial_balance(self)

    @staticmethod
    def get_credit_and_debit_values(account: "TAccount") -> tuple[float, float]:
        """Get the debit and credit values for the given account."""
        if account.normal_balance == AccountNormalBalance.DEBIT_NORMAL:
            return (account.balance(), 0)
        return (0, account.balance())


@dataclass
class IncomeStatement(Statement):
    """Class representing an income statement."""

    income: AccountBalances
    expenses: AccountBalances
    name = "Income Statement"

    @classmethod
    def from_ledger(cls, ledger: "Ledger") -> "IncomeStatement":
        """Create an IncomeStatement from the given ledger."""
        income_statement = cls(
            income=AccountBalances.from_accounts(ledger.get_accounts_by_type(AccountType.INCOME)),
            expenses=AccountBalances.from_accounts(ledger.get_accounts_by_type(AccountType.EXPENSE)),
        )
        income_statement.date = ledger.date_closed
        return income_statement

    def accept(self, visitor: "StatementVisitor") -> str:
        """Accept a StatementVisitor to generate a view of the statement."""
        return visitor.visit_income_statement(self)


@dataclass
class BalanceSheet(Statement):
    """Class representing a balance sheet."""

    assets: AccountBalances
    liabilities: AccountBalances
    equities: AccountBalances
    name = "Balance Sheet"

    @classmethod
    def from_ledger(cls, ledger: "Ledger") -> "BalanceSheet":
        """Create a BalanceSheet from the given ledger."""
        balance_sheet = cls(
            assets=AccountBalances.from_accounts(ledger.get_accounts_by_type(AccountType.ASSET)),
            liabilities=AccountBalances.from_accounts(ledger.get_accounts_by_type(AccountType.LIABILITY)),
            equities=AccountBalances.from_accounts(ledger.get_accounts_by_type(AccountType.EQUITY)),
        )
        balance_sheet.date = ledger.date_closed
        return balance_sheet

    def accept(self, visitor: "StatementVisitor") -> str:
        """Accept a StatementVisitor to generate a view of the statement."""
        return visitor.visit_balance_sheet(self)


class Report:
    """Class for generating financial reports."""

    def __init__(self, ledger: "Ledger", viewer: "StatementVisitor", date: datetime.date) -> None:
        """Initialize the statements from the ledger."""
        # Report should not alter the ledger so we make a copy.
        # This is a design choice - there can be multiple report instances using the same ledger.
        self.ledger = deepcopy(ledger)
        self.viewer = viewer
        self.date = date

        self.trial_balance = TrialBalance.from_ledger(deepcopy(self.ledger))
        self.trial_balance.date = self.date
        # Close contra income and contra expense accounts for income statement
        self.ledger.close_contra_accounts(self.date)
        self.income_statement = IncomeStatement.from_ledger(deepcopy(self.ledger))
        # Close income and expense accounts to ISA and close ISA to retained earnings account
        self.ledger.close_income_and_expense_accounts(self.date)
        self.ledger.close_income_summary_account(self.date)
        self.balance_sheet = BalanceSheet.from_ledger(self.ledger)

    def print_trial_balance(self) -> None:
        """Generate the trial balance view."""
        self.trial_balance.accept(self.viewer)

    def print_income_statement(self) -> None:
        """Generate the income statement view."""
        self.income_statement.accept(self.viewer)

    def print_balance_sheet(self) -> None:
        """Generate the balance sheet view."""
        self.balance_sheet.accept(self.viewer)

    def get_total_assets(self) -> float:
        """Calculate and return the bank's total assets."""
        return sum(self.balance_sheet.assets.values())

    def get_total_liabilities(self) -> float:
        """Calculate and return the bank's total liabilities."""
        return sum(self.balance_sheet.liabilities.values())

    def get_total_equity(self) -> float:
        """Calculate and return the bank's total equity."""
        return sum(self.balance_sheet.equities.values())

    def get_cet1(self) -> float:
        """Calculate and return the bank's CET1 capital."""
        cet1 = 0.0
        for account, balance in self.balance_sheet.equities.items():
            if isinstance(account, EquityAccount):
                cet1 += balance
            if isinstance(account, AccumulatedOCIAccount):
                cet1 += balance
            if isinstance(account, RetainedEarningsAccount):
                cet1 += balance
        return cet1

    def get_cet1_ratio(self) -> float:
        """Calculate and return the bank's CET1 ratio."""
        return 0.0

    def get_tier1_capital_ratio(self) -> float:
        """Calculate and return the bank's Tier 1 capital ratio."""
        return 0.0

    def get_total_capital_ratio(self) -> float:
        """Calculate and return the bank's total capital ratio."""
        return 0.0

    def get_net_stable_funding_ratio(self) -> float:
        """Calculate and return the bank's Net Stable Funding Ratio (NSFR)."""
        return 0.0

    def get_liquidity_coverage_ratio(self) -> float:
        """Calculate and return the bank's Liquidity Coverage Ratio (LCR)."""
        return 0.0
