"""Controller for transaction history view — subscribes to TransactionsRecorded."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QLocale

from brms.app.controllers.base import BRMSController
from brms.core.enums import TransactionType
from brms.core.events import TransactionsRecorded

if TYPE_CHECKING:
    from brms.app.views.transaction_history.transaction_history_widget import BRMSTransactionHistoryWidget
    from brms.core.events import EventBus
    from brms.core.models.accounting.journal import Journal
    from brms.core.models.transaction import Transaction
    from brms.core.stores.transaction_log import TransactionLog


class TransactionHistoryController(BRMSController):
    """Subscribes to TransactionsRecorded, transforms transactions to view-ready dicts."""

    def __init__(
        self,
        view: BRMSTransactionHistoryWidget,
        event_bus: EventBus,
        transaction_log: TransactionLog,
        journal: Journal,
    ) -> None:
        """Initialize the transaction history controller."""
        super().__init__()
        self.view = view
        self._transaction_log = transaction_log
        self._journal = journal
        self._pushed_tx_ids: set[str] = set()
        self._tx_count = 0
        self._locale = QLocale()

        self.view.type_filter.clear()
        self.view.type_filter.addItem("All")
        for tx_type in TransactionType:
            self.view.type_filter.addItem(tx_type.name.replace("_", " ").title())

        event_bus.subscribe(TransactionsRecorded, self._on_transactions_recorded)
        self.view.transaction_tree.selectionModel().selectionChanged.connect(self._on_selection_changed)

    def load_initial(self) -> None:
        """Load all existing transactions from the log into the view."""
        for tx in self._transaction_log.all():
            if tx.id not in self._pushed_tx_ids:
                self.view.add_row(self._format_transaction(tx))
                self._pushed_tx_ids.add(tx.id)
                self._tx_count += 1
        self.view.flush_transactions()

    def _on_transactions_recorded(self, event: TransactionsRecorded) -> None:
        for tx in event.transactions:
            if tx.id not in self._pushed_tx_ids:
                self.view.add_row(self._format_transaction(tx))
                self._pushed_tx_ids.add(tx.id)
                self._tx_count += 1

    def _on_selection_changed(self) -> None:
        """Look up journal entries for the selected transaction and display them."""
        indexes = self.view.transaction_tree.selectedIndexes()
        if not indexes:
            return
        item = indexes[0].internalPointer()
        tx_id = item.data(6)  # hidden column stores transaction id
        if not tx_id:
            return
        html = self._journal_html_for_tx(tx_id)
        self.view.journal_display.setText(html)

    def _journal_html_for_tx(self, tx_id: str) -> str:
        """Build HTML table showing journal entries associated with a transaction."""
        marker = f"tx={tx_id}"
        entries = [e for e in self._journal.entries if marker in e.description]
        if not entries:
            return "<i>No journal entry found</i>"

        parts: list[str] = []
        for entry in entries:
            rows = ""
            for acct, amt in entry.debit_account_value_pairs():
                rows += (
                    f"<tr><td style='padding:2px 8px'>Dr</td>"
                    f"<td>{acct.name}</td>"
                    f"<td align='right'>{amt:,.2f}</td></tr>"
                )
            for acct, amt in entry.credit_account_value_pairs():
                rows += (
                    f"<tr><td style='padding:2px 8px'>Cr</td>"
                    f"<td>&nbsp;&nbsp;{acct.name}</td>"
                    f"<td align='right'>{amt:,.2f}</td></tr>"
                )
            date_str = str(entry.date) if entry.date else ""
            # Strip the internal "(tx=...)" marker from the display description
            desc = entry.description.split(" (tx=")[0] if " (tx=" in entry.description else entry.description
            parts.append(
                f"<b>{desc}</b><br>"
                f"<span style='color:gray'>{date_str}</span>"
                f"<table style='margin-top:4px'>{rows}</table>",
            )
        return "<br>".join(parts)

    def _format_transaction(self, transaction: Transaction) -> dict:
        type_label = transaction.type.name.replace("_", " ").title()
        description = transaction.description or type_label
        return {
            0: self._tx_count,
            1: str(transaction.date),
            2: type_label,
            3: transaction.instrument_id or "",
            4: self._locale.toCurrencyString(float(transaction.amount)),
            5: description,
            6: transaction.id,
        }
