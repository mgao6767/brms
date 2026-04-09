"""HTML rendering of financial statements using rich."""

from __future__ import annotations

import locale
from io import StringIO
from typing import TYPE_CHECKING

import rich.box
from rich.console import Console
from rich.table import Table
from rich.text import Text

if TYPE_CHECKING:
    import datetime

try:
    locale.setlocale(locale.LC_ALL, "en_AU.UTF-8")
except locale.Error:
    try:
        locale.setlocale(locale.LC_ALL, "")
    except locale.Error:
        locale.setlocale(locale.LC_ALL, "C")


def _format_amount(amount: float) -> Text:
    """Return a Text object styled green for non-negative, red for negative values."""
    formatted = f"${amount:,.2f}" if amount >= 0 else f"(${abs(amount):,.2f})"
    style = "green" if amount >= 0 else "red"
    return Text(formatted, style=style)


def _export_html(table: Table) -> str:
    """Render *table* to an HTML string via a recording Console."""
    console = Console(record=True, file=StringIO())
    console.print(table)
    return console.export_html(clear=False)


class HTMLStatementRenderer:
    """Render structured financial-statement data as HTML using rich."""

    def render_trial_balance(
        self,
        data: list[dict],
        date: datetime.date | str | None = None,
    ) -> str:
        """Render a trial balance as an HTML table.

        Parameters
        ----------
        data:
            List of dicts with keys ``account``, ``debit``, ``credit``, ``balance``.
        date:
            Optional statement date shown as a caption.

        """
        caption = f"Date: {date}" if date is not None else None
        table = Table(
            title="Trial Balance",
            box=rich.box.HORIZONTALS,
            caption=caption,
            caption_justify="right",
        )
        table.add_column("Account", justify="left", no_wrap=True)
        table.add_column("Debit", justify="right")
        table.add_column("Credit", justify="right")

        total_debit = 0.0
        total_credit = 0.0
        for row in data:
            table.add_row(row["account"], _format_amount(row["debit"]), _format_amount(row["credit"]))
            total_debit += row["debit"]
            total_credit += row["credit"]

        table.add_section()
        table.add_row("Total", _format_amount(total_debit), _format_amount(total_credit), style="bold")

        return _export_html(table)

    def render_balance_sheet(
        self,
        data: dict,
        date: datetime.date | str | None = None,
    ) -> str:
        """Render a balance sheet as an HTML table.

        Parameters
        ----------
        data:
            Dict with keys ``assets``, ``liabilities``, ``equity`` (lists of
            ``{"account": str, "balance": float}``), plus ``total_assets``,
            ``total_liabilities``, ``total_equity``.
        date:
            Optional statement date shown as a caption.

        """
        caption = f"Date: {date}" if date is not None else None
        table = Table(
            title="Balance Sheet",
            box=rich.box.HORIZONTALS,
            caption=caption,
            caption_justify="right",
            show_header=False,
        )
        table.add_column(justify="left", no_wrap=True)
        table.add_column(justify="right")

        # Assets
        table.add_row("Assets", style="bold")
        for item in data.get("assets", []):
            table.add_row(item["account"], _format_amount(item["balance"]))
        table.add_row("Total Assets", _format_amount(data.get("total_assets", 0.0)), style="bold")
        table.add_section()

        # Liabilities
        table.add_row("Liabilities", style="bold")
        for item in data.get("liabilities", []):
            table.add_row(item["account"], _format_amount(item["balance"]))
        table.add_row("Total Liabilities", _format_amount(data.get("total_liabilities", 0.0)), style="bold")
        table.add_section()

        # Equity
        table.add_row("Equity", style="bold")
        for item in data.get("equity", []):
            table.add_row(item["account"], _format_amount(item["balance"]))
        table.add_row("Total Equity", _format_amount(data.get("total_equity", 0.0)), style="bold")

        return _export_html(table)

    def render_income_statement(
        self,
        data: dict,
        date: datetime.date | str | None = None,
    ) -> str:
        """Render an income statement as an HTML table.

        Parameters
        ----------
        data:
            Dict with keys ``income``, ``expenses`` (lists of
            ``{"account": str, "balance": float}``), plus ``total_income``,
            ``total_expenses``, ``net_income``.
        date:
            Optional statement date shown as a caption.

        """
        caption = f"Date: {date}" if date is not None else None
        table = Table(
            title="Income Statement",
            box=rich.box.HORIZONTALS,
            caption=caption,
            caption_justify="right",
            show_header=False,
        )
        table.add_column(justify="left", no_wrap=True)
        table.add_column(justify="right")

        # Income
        table.add_row("Income", style="bold")
        for item in data.get("income", []):
            table.add_row(item["account"], _format_amount(item["balance"]))
        table.add_row("Total Income", _format_amount(data.get("total_income", 0.0)), style="bold")
        table.add_section()

        # Expenses
        table.add_row("Expenses", style="bold")
        for item in data.get("expenses", []):
            table.add_row(item["account"], _format_amount(item["balance"]))
        table.add_row("Total Expenses", _format_amount(data.get("total_expenses", 0.0)), style="bold")
        table.add_section()

        # Net Income
        table.add_row("Net Income", _format_amount(data.get("net_income", 0.0)), style="bold")

        return _export_html(table)
