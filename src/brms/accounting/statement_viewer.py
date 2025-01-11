"""Module for generating views of accounting statements."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from brms.accounting.report import BalanceSheet, IncomeStatement, TrialBalance


class StatementVisitor(ABC):
    """Interface for statement visitors."""

    @abstractmethod
    def visit_trial_balance(self, statement: "TrialBalance") -> str:
        """Generate view for TrialBalance."""

    @abstractmethod
    def visit_income_statement(self, statement: "IncomeStatement") -> str:
        """Generate view for IncomeStatement."""

    @abstractmethod
    def visit_balance_sheet(self, statement: "BalanceSheet") -> str:
        """Generate view for BalanceSheet."""


class HTMLStatementViewer(StatementVisitor):
    """Concrete visitor for generating HTML view of statements."""

    def visit_trial_balance(self, statement: "TrialBalance") -> str:
        """Generate view for TrialBalance."""
        raise NotImplementedError

    def visit_income_statement(self, statement: "IncomeStatement") -> str:
        """Generate view for IncomeStatement."""
        raise NotImplementedError

    def visit_balance_sheet(self, statement: "BalanceSheet") -> str:
        """Generate view for BalanceSheet."""
        raise NotImplementedError


class TextStatementViewer(StatementVisitor):
    """Concrete visitor for generating plain text view of statements."""

    def visit_trial_balance(self, statement: "TrialBalance") -> str:
        """Generate view for TrialBalance."""
        raise NotImplementedError

    def visit_income_statement(self, statement: "IncomeStatement") -> str:
        """Generate view for IncomeStatement."""
        raise NotImplementedError

    def visit_balance_sheet(self, statement: "BalanceSheet") -> str:
        """Generate view for BalanceSheet."""
        raise NotImplementedError
