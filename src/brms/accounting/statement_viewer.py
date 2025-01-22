"""Module for generating views of accounting statements."""

import locale
from abc import ABC, abstractmethod
from io import StringIO
from typing import TYPE_CHECKING

import rich.box
from rich.console import Console
from rich.padding import Padding
from rich.table import Table
from rich.text import Text

from brms.accounting.account import AccountType, TAccount

if TYPE_CHECKING:
    from brms.accounting.report import BalanceSheet, IncomeStatement, TrialBalance

try:
    locale.setlocale(locale.LC_ALL, "en_AU.UTF-8")
except locale.Error:
    try:
        locale.setlocale(locale.LC_ALL, "")
    except locale.Error:
        locale.setlocale(locale.LC_ALL, "C")


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

    def __init__(
        self,
        *,
        padding: int = 2,
        trial_balance_table_width: int | None = None,
        income_statement_table_width: int | None = None,
        balance_sheet_table_width: int | None = None,
        console: bool = True,
        jupyter: bool = False,
        hide_zero_balance_accounts: bool = False,
    ) -> None:
        super().__init__()
        self.padding = padding
        self.trial_balance_table_width = trial_balance_table_width
        self.income_statement_table_width = income_statement_table_width
        self.balance_sheet_table_width = balance_sheet_table_width
        self.console = console
        self.jupyter = jupyter
        self.hide_zero_balance_accounts = hide_zero_balance_accounts

    @staticmethod
    def format_amount(amount: float) -> Text:
        """Return Text object with green for positive and red for negative values."""
        if amount >= 0:
            formatted_amount = locale.currency(amount, grouping=True)
            return Text(formatted_amount, style="green")
        formatted_amount = locale.currency(abs(amount), grouping=True)
        return Text(f"({formatted_amount})", style="red")

    def add_account_balance_rows(self, account: TAccount, table: Table, account_level: int = 1) -> None:
        """Recursively add account rows to the table."""
        if self.hide_zero_balance_accounts and account.balance() == 0:
            return
        name = Padding(account.name, pad=(0, self.padding * account_level))
        table.add_row(name, self.format_amount(account.balance()))
        for sub in account.sub_accounts:
            self.add_account_balance_rows(sub, table, account_level + 1)

    def add_account_debit_credit_rows(
        self,
        account: TAccount,
        statement: "TrialBalance",
        table: Table,
        account_level: int = 1,
    ) -> None:
        """Recursively add account rows to the table."""
        name = Padding(account.name, pad=(0, self.padding * account_level))
        dr, cr = statement.get_credit_and_debit_values(account)
        table.add_row(name, self.format_amount(dr), self.format_amount(cr))
        for sub in account.sub_accounts:
            self.add_account_debit_credit_rows(sub, statement, table, account_level + 1)

    def visit_trial_balance(self, statement: "TrialBalance") -> str:
        """Generate view for TrialBalance."""
        caption = f"Date: {statement.date}"
        table = Table(
            title=statement.name,
            box=rich.box.HORIZONTALS,
            caption=caption,
            caption_justify="right",
            width=self.trial_balance_table_width,
        )
        table.add_column("Account", justify="left", no_wrap=True)
        table.add_column("Debit", justify="right")
        table.add_column("Credit", justify="right")

        total_dr, total_cr = 0.0, 0.0
        for account_type in AccountType:
            table.add_row(f"{account_type.value.capitalize()} Account", style="italic")
            for account, (dr, cr) in statement.items():
                if account.type == account_type:
                    self.add_account_debit_credit_rows(account, statement, table)
                    total_dr += dr
                    total_cr += cr
            table.add_section()
        table.add_row("Total", self.format_amount(total_dr), self.format_amount(total_cr), style="bold")

        console = Console(
            record=True,
            file=StringIO() if not self.console else None,  # print to StringIO to avoid printing to terminal
            force_jupyter=self.jupyter,  # whether to automatically print in jupyter notebook
        )
        console.print(table)
        statement.text = console.export_text(clear=False)
        statement.html = console.export_html(clear=False)
        return statement.html

    def visit_income_statement(self, statement: "IncomeStatement") -> str:
        """Generate view for IncomeStatement."""
        total_income = sum(statement.income.values())
        total_expense = sum(statement.expenses.values())
        profit = total_income - total_expense

        caption = f"Date: {statement.date}"
        table = Table(
            title=statement.name,
            box=rich.box.HORIZONTALS,
            caption=caption,
            caption_justify="right",
            show_header=False,
            width=self.income_statement_table_width,
        )
        table.add_column(justify="left", no_wrap=True)
        table.add_column(justify="right", style="green")

        table.add_row("Income", self.format_amount(total_income), style="bold")
        for account in statement.income:
            if not (account.is_contra_account or account.is_temporary_account):
                self.add_account_balance_rows(account, table)
        table.add_section()
        table.add_row("Expense", self.format_amount(total_expense), style="bold")
        for account in statement.expenses:
            if not (account.is_contra_account or account.is_temporary_account):
                self.add_account_balance_rows(account, table)
        table.add_section()
        table.add_row("Profit", self.format_amount(profit), style="bold")

        console = Console(
            record=True,
            file=StringIO() if not self.console else None,  # print to StringIO to avoid printing to terminal
            force_jupyter=self.jupyter,  # whether to automatically print in jupyter notebook
        )
        console.print(table)
        statement.text = console.export_text(clear=False)
        statement.html = console.export_html(clear=False)
        return statement.html

    def visit_balance_sheet(self, statement: "BalanceSheet") -> str:
        """Generate view for BalanceSheet."""
        total_assets = sum(statement.assets.values())
        total_liabilities = sum(statement.liabilities.values())
        total_equity = sum(statement.equities.values())
        net_assets = total_assets - total_liabilities

        caption = f"Date: {statement.date}"
        table = Table(
            title=statement.name,
            box=rich.box.HORIZONTALS,
            caption=caption,
            caption_justify="right",
            show_header=False,
            width=self.balance_sheet_table_width,
        )
        table.add_column(justify="left", no_wrap=True)
        table.add_column(justify="right", style="green")

        # Assets
        table.add_row("Assets", style="bold")
        for account in statement.assets:
            if not (account.is_contra_account or account.is_temporary_account):
                self.add_account_balance_rows(account, table)
        table.add_row("Total assets", self.format_amount(total_assets), style="bold")
        table.add_section()
        # Liabilities
        table.add_row("Liabilities", style="bold")
        for account in statement.liabilities:
            if not (account.is_contra_account or account.is_temporary_account):
                self.add_account_balance_rows(account, table)
        table.add_row("Total liabilities", self.format_amount(total_liabilities), style="bold")
        table.add_section()
        # Net assets
        table.add_row("Net assets", self.format_amount(net_assets), style="bold")
        table.add_section()
        # Shareholders' equity
        table.add_row("Shareholders' equity", style="bold")
        for account in statement.equities:
            if not (account.is_contra_account or account.is_temporary_account):
                self.add_account_balance_rows(account, table)
        table.add_row("Total shareholders' equity", self.format_amount(total_equity), style="bold")

        console = Console(
            record=True,
            file=StringIO() if not self.console else None,  # print to StringIO to avoid printing to terminal
            force_jupyter=self.jupyter,  # whether to automatically print in jupyter notebook
        )
        console.print(table)
        statement.text = console.export_text(clear=False)
        statement.html = console.export_html(clear=False)
        return statement.html


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
