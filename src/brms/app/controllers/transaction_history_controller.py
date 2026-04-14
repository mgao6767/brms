"""Controller for transaction history view — subscribes to TransactionsRecorded."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt

from brms.app.controllers.base import BRMSController
from brms.core.enums import TransactionType
from brms.core.events import DateAdvanced, TransactionsRecorded

if TYPE_CHECKING:
    import datetime

    from brms.app.controllers.inspector_controller import InspectorController
    from brms.app.views.transaction_history.transaction_history_widget import BRMSTransactionHistoryWidget
    from brms.core.events import EventBus
    from brms.core.models.transaction import Transaction
    from brms.core.stores.transaction_log import TransactionLog


class TransactionHistoryController(BRMSController):
    """Subscribes to TransactionsRecorded, transforms transactions to view-ready dicts."""

    def __init__(  # noqa: PLR0913
        self,
        view: BRMSTransactionHistoryWidget,
        event_bus: EventBus,
        transaction_log: TransactionLog,
        inspector_ctrl: InspectorController,
        start_date: datetime.date | None = None,
        end_date: datetime.date | None = None,
    ) -> None:
        """Initialize the transaction history controller."""
        super().__init__()
        self.view = view
        self._transaction_log = transaction_log
        self._inspector_ctrl = inspector_ctrl
        self._pushed_tx_ids: set[str] = set()
        self._tx_count = 0
        self._filter_active = False

        # Populate type filter — sorted alphabetically
        type_labels = sorted(t.name.replace("_", " ").title() for t in TransactionType)
        self.view.type_filter.clear()
        self.view.type_filter.addItem("All")
        for label in type_labels:
            self.view.type_filter.addItem(label)

        # Initialize date filters from simulation dates
        if start_date:
            self.view.set_start_date(start_date)
        if end_date:
            self.view.set_end_date(end_date)

        event_bus.subscribe(TransactionsRecorded, self._on_transactions_recorded)
        event_bus.subscribe(DateAdvanced, self._on_date_advanced)
        self.view.transaction_tree.selectionModel().selectionChanged.connect(self._on_selection_changed)
        self.view.search_button.clicked.connect(self._on_search)
        self.view.reset_button.clicked.connect(self._on_reset)
        # Re-apply filter after flush adds rows to the model
        self.view.transactions_tree_model.layoutChanged.connect(self._enforce_filter)

    def reset(self) -> None:
        """Clear all transaction data from the view."""
        self.view.transactions_tree_model.blockSignals(True)
        self.view.transaction_tree.clear_data()
        self.view.transactions_tree_model.blockSignals(False)
        self.view._transaction_buffer.clear()  # noqa: SLF001
        self._pushed_tx_ids.clear()
        self._tx_count = 0
        self._filter_active = False
        self.view.set_filter_indicator(active=False)

    def load_initial(self) -> None:
        """Load all existing transactions from the log into the view."""
        for tx in self._transaction_log.all():
            if tx.id not in self._pushed_tx_ids:
                self.view.add_row(self._format_transaction(tx))
                self._pushed_tx_ids.add(tx.id)
                self._tx_count += 1
        self.view.flush_transactions()

    def _on_date_advanced(self, event: DateAdvanced) -> None:
        """Update the end date filter to the current simulation date."""
        self.view.set_end_date(event.date)

    def _on_transactions_recorded(self, event: TransactionsRecorded) -> None:
        for tx in event.transactions:
            if tx.id not in self._pushed_tx_ids:
                self.view.add_row(self._format_transaction(tx))
                self._pushed_tx_ids.add(tx.id)
                self._tx_count += 1

    def _enforce_filter(self) -> None:
        """Re-apply active filter after new rows are flushed to the model."""
        if self._filter_active:
            self.view.search_transactions()

    def _on_search(self) -> None:
        """Handle search button — apply filter and show indicator."""
        self._filter_active = True
        self.view.search_transactions()
        self.view.set_filter_indicator(active=True)

    def _on_reset(self) -> None:
        """Handle reset button — clear filter and hide indicator."""
        self._filter_active = False
        self.view.reset_filters()
        self.view.sort_proxy.sort(-1, Qt.SortOrder.AscendingOrder)
        self.view.set_filter_indicator(active=False)

    def filter_by_instrument(self, instrument_id: str) -> None:
        """Set the instrument filter and trigger search."""
        self.view.instrument_filter.setText(instrument_id)
        self._on_search()

    def _on_selection_changed(self) -> None:
        """Look up the selected transaction and show its details in the inspector."""
        indexes = self.view.transaction_tree.selectedIndexes()
        if not indexes:
            return
        # Map proxy index to source model index to access TreeItem
        proxy_index = indexes[0]
        source_index = self.view.sort_proxy.mapToSource(proxy_index)
        item = source_index.internalPointer()
        tx_id = item.data(6)  # hidden column stores transaction id
        if not tx_id:
            return
        try:
            tx = self._transaction_log.get(tx_id)
        except KeyError:
            return
        self._inspector_ctrl.show_transaction_details(tx)

    def _format_transaction(self, transaction: Transaction) -> dict:
        type_label = transaction.type.name.replace("_", " ").title()
        description = transaction.description or type_label
        return {
            0: self._tx_count,
            1: str(transaction.date),
            2: type_label,
            3: transaction.instrument_id or "",
            4: float(transaction.amount),
            5: description,
            6: transaction.id,
        }
