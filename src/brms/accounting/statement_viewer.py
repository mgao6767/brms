"""Module for generating views of accounting statements."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from rich.console import Console
from rich.padding import Padding
from rich.table import Table

from brms.accounting.account import AccountType

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

    console = Console(record=True)

    def visit_trial_balance(self, statement: "TrialBalance") -> str:
        """Generate view for TrialBalance."""
        caption = f"Date: {statement.date}"
        table = Table(title=statement.name, box=None, caption=caption, caption_justify="right")
        table.add_column("Account", justify="left", no_wrap=True)
        table.add_column("Debit", justify="right", style="green")
        table.add_column("Credit", justify="right", style="green")

        total_dr, total_cr = 0.0, 0.0
        for account_type in AccountType:
            table.add_row(f"{account_type.value.capitalize()} Account", style="italic")
            for account, (dr, cr) in statement.items():
                if account.type == account_type:
                    name = Padding(account.name, pad=(0, 2))
                    table.add_row(name, f"{dr:.2f}", f"{cr:.2f}")
                    total_dr += dr
                    total_cr += cr

        table.add_row("Total", f"{total_dr:.2f}", f"{total_cr:.2f}", style="bold")

        with self.console.capture() as capture:
            self.console.print(table)
        return capture.get()

    def visit_income_statement(self, statement: "IncomeStatement") -> str:
        """Generate view for IncomeStatement."""
        total_income = sum(statement.income.values())
        total_expense = sum(statement.expenses.values())
        profit = total_income - total_expense

        caption = f"Date: {statement.date}"
        table = Table(title=statement.name, box=None, caption=caption, caption_justify="right", show_header=False)
        table.add_column(justify="left", no_wrap=True)
        table.add_column(justify="right", style="green")

        table.add_row("Income", f"{total_income:.2f}", style="bold")
        for account, balance in statement.income.items():
            if not (account.is_contra_account or account.is_temporary_account):
                name = Padding(account.name, pad=(0, 2))
                table.add_row(name, f"{balance:.2f}")
        table.add_row("Expense", f"{total_expense:.2f}", style="bold")
        for account, balance in statement.expenses.items():
            if not (account.is_contra_account or account.is_temporary_account):
                name = Padding(account.name, pad=(0, 2))
                table.add_row(name, f"{balance:.2f}")
        table.add_row("Profit", f"{profit:.2f}", style="bold")

        with self.console.capture() as capture:
            self.console.print(table)
        return capture.get()

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
