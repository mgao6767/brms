"""Provides classes for generating financial statements and reports."""

from abc import ABC, abstractmethod
from collections import UserDict
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from brms.accounting.account import AccountBalances, AccountNormalBalance, AccountType

if TYPE_CHECKING:
    from brms.accounting.account import TAccount
    from brms.accounting.ledger import Ledger
    from brms.accounting.statement_viewer import StatementVisitor


class Statement(ABC):
    """Abstract base class for statements."""

    @classmethod
    @abstractmethod
    def from_ledger(cls, ledger: "Ledger") -> "Statement":
        """Create a statement from the given ledger."""

    @abstractmethod
    def accept(self, visitor: "StatementVisitor") -> str:
        """Accept a StatementVisitor to generate a view of the statement."""


class TrialBalance(UserDict["TAccount", tuple[float, float]], Statement):
    """Class representing a trial balance."""

    @classmethod
    def from_ledger(cls, ledger: "Ledger") -> "TrialBalance":
        """Create a TrialBalance from the given ledger."""
        trial_balance = cls()
        for account, balance in ledger.account_balances().items():
            dr = balance if account.normal_balance == AccountNormalBalance.DEBIT_NORMAL else 0.0
            cr = balance if account.normal_balance == AccountNormalBalance.CREDIT_NORMAL else 0.0
            trial_balance[account] = (dr, cr)
        return trial_balance

    def accept(self, visitor: "StatementVisitor") -> str:
        """Accept a StatementVisitor to generate a view of the statement."""
        return visitor.visit_trial_balance(self)


@dataclass
class IncomeStatement(Statement):
    """Class representing an income statement."""

    income: AccountBalances
    expenses: AccountBalances

    @classmethod
    def from_ledger(cls, ledger: "Ledger") -> "IncomeStatement":
        """Create an IncomeStatement from the given ledger."""
        return cls(
            income=AccountBalances.from_accounts(ledger.get_accounts_by_type(AccountType.INCOME)),
            expenses=AccountBalances.from_accounts(ledger.get_accounts_by_type(AccountType.EXPENSE)),
        )

    def accept(self, visitor: "StatementVisitor") -> str:
        """Accept a StatementVisitor to generate a view of the statement."""
        return visitor.visit_income_statement(self)


@dataclass
class BalanceSheet(Statement):
    """Class representing a balance sheet."""

    assets: AccountBalances
    liabilities: AccountBalances
    equities: AccountBalances

    @classmethod
    def from_ledger(cls, ledger: "Ledger") -> "BalanceSheet":
        """Create a BalanceSheet from the given ledger."""
        return cls(
            assets=AccountBalances.from_accounts(ledger.get_accounts_by_type(AccountType.ASSET)),
            liabilities=AccountBalances.from_accounts(ledger.get_accounts_by_type(AccountType.LIABILITY)),
            equities=AccountBalances.from_accounts(ledger.get_accounts_by_type(AccountType.EQUITY)),
        )

    def accept(self, visitor: "StatementVisitor") -> str:
        """Accept a StatementVisitor to generate a view of the statement."""
        return visitor.visit_balance_sheet(self)


@dataclass
class Report:
    """Class for generating financial reports."""

    ledger: "Ledger"
    viewer: "StatementVisitor"

    def __post_init__(self) -> None:
        """Initialize the income statement and balance sheet from the ledger."""
        self.income_statement = IncomeStatement.from_ledger(self.ledger)
        self.balance_sheet = BalanceSheet.from_ledger(self.ledger)
        self.trial_balance = TrialBalance.from_ledger(self.ledger)

    def print_trial_balance(self) -> str:
        """Generate the trial balance view."""
        return self.trial_balance.accept(self.viewer)

    def print_income_statement(self) -> str:
        """Generate the income statement view."""
        return self.income_statement.accept(self.viewer)

    def print_balance_sheet(self) -> str:
        """Generate the balance sheet view."""
        return self.balance_sheet.accept(self.viewer)
