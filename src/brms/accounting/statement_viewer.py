"""Module for generating views of accounting statements."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from rich.console import Console
from rich.padding import Padding
from rich.table import Table
from rich.text import Text

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

    @staticmethod
    def format_amount(amount: float) -> Text:
        """Return Text object with green for positive and red for negative values."""
        color = "green" if amount >= 0 else "red"
        return Text(f"{amount:.2f}", style=color)

    def visit_trial_balance(self, statement: "TrialBalance") -> str:
        """Generate view for TrialBalance."""
        caption = f"Date: {statement.date}"
        table = Table(title=statement.name, box=None, caption=caption, caption_justify="right")
        table.add_column("Account", justify="left", no_wrap=True)
        table.add_column("Debit", justify="right")
        table.add_column("Credit", justify="right")

        total_dr, total_cr = 0.0, 0.0
        for account_type in AccountType:
            table.add_row(f"{account_type.value.capitalize()} Account", style="italic")
            for account, (dr, cr) in statement.items():
                if account.type == account_type:
                    name = Padding(account.name, pad=(0, 2))
                    table.add_row(name, self.format_amount(dr), self.format_amount(cr))
                    total_dr += dr
                    total_cr += cr

        table.add_row("Total", self.format_amount(total_dr), self.format_amount(total_cr), style="bold")

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

        table.add_row("Income", self.format_amount(total_income), style="bold")
        for account, balance in statement.income.items():
            if not (account.is_contra_account or account.is_temporary_account):
                name = Padding(account.name, pad=(0, 2))
                table.add_row(name, self.format_amount(balance))
        table.add_row("Expense", self.format_amount(total_expense), style="bold")
        for account, balance in statement.expenses.items():
            if not (account.is_contra_account or account.is_temporary_account):
                name = Padding(account.name, pad=(0, 2))
                table.add_row(name, self.format_amount(balance))
        table.add_row("Profit", self.format_amount(profit), style="bold")

        with self.console.capture() as capture:
            self.console.print(table)
        return capture.get()

    def visit_balance_sheet(self, statement: "BalanceSheet") -> str:
        """Generate view for BalanceSheet."""
        total_assets = sum(statement.assets.values())
        total_liabilities = sum(statement.liabilities.values())
        total_equity = sum(statement.equities.values())
        net_assets = total_assets - total_liabilities

        caption = f"Date: {statement.date}"
        table = Table(title=statement.name, box=None, caption=caption, caption_justify="right", show_header=False)
        table.add_column(justify="left", no_wrap=True)
        table.add_column(justify="right", style="green")

        # Assets
        table.add_row("Assets", style="bold")
        for account, balance in statement.assets.items():
            if not (account.is_contra_account or account.is_temporary_account):
                name = Padding(account.name, pad=(0, 2))
                table.add_row(name, self.format_amount(balance))
        table.add_row("Total assets", self.format_amount(total_assets), style="bold")
        # Liabilities
        table.add_row("Liabilities", style="bold")
        for account, balance in statement.liabilities.items():
            if not (account.is_contra_account or account.is_temporary_account):
                name = Padding(account.name, pad=(0, 2))
                table.add_row(name, self.format_amount(balance))
        table.add_row("Total liabilities", self.format_amount(total_liabilities), style="bold")
        # Net assets
        table.add_row("Net assets", self.format_amount(net_assets), style="bold")
        # Shareholders' equity
        table.add_row("Shareholders' equity", style="bold")
        for account, balance in statement.equities.items():
            if not (account.is_contra_account or account.is_temporary_account):
                name = Padding(account.name, pad=(0, 2))
                table.add_row(name, self.format_amount(balance))
        table.add_row("Total shareholders' equity", self.format_amount(total_equity), style="bold")

        with self.console.capture() as capture:
            self.console.print(table)
        return capture.get()


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
