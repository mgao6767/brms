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
    from brms.core.models.transaction import Transaction
    from brms.core.stores.transaction_log import TransactionLog


class TransactionHistoryController(BRMSController):
    """Subscribes to TransactionsRecorded, transforms transactions to view-ready dicts."""

    def __init__(
        self,
        view: BRMSTransactionHistoryWidget,
        event_bus: EventBus,
        transaction_log: TransactionLog,
    ) -> None:
        """Initialize the transaction history controller."""
        super().__init__()
        self.view = view
        self._transaction_log = transaction_log
        self._pushed_tx_ids: set[str] = set()
        self._tx_count = 0
        self._locale = QLocale()

        self.view.type_filter.clear()
        self.view.type_filter.addItem("All")
        for tx_type in TransactionType:
            self.view.type_filter.addItem(tx_type.name)

        event_bus.subscribe(TransactionsRecorded, self._on_transactions_recorded)

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
            6: "",
        }
