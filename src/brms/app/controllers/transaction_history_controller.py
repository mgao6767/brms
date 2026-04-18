"""Controller for transaction history view — subscribes to TransactionsRecorded."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QModelIndex, Qt

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
    """Subscribes to TransactionsRecorded, transforms transactions to view-ready tuples."""

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

        type_labels = sorted(t.name.replace("_", " ").title() for t in TransactionType)
        self.view.type_filter.clear()
        self.view.type_filter.addItem("All")
        for label in type_labels:
            self.view.type_filter.addItem(label)

        if start_date:
            self.view.set_start_date(start_date)
        if end_date:
            self.view.set_end_date(end_date)

        event_bus.subscribe(TransactionsRecorded, self._on_transactions_recorded)
        event_bus.subscribe(DateAdvanced, self._on_date_advanced)
        self.view.table_view.selectionModel().selectionChanged.connect(self._on_selection_changed)
        self.view.table_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.view.table_view.customContextMenuRequested.connect(self._on_context_menu)
        self.view.search_button.clicked.connect(self._on_search)
        self.view.reset_button.clicked.connect(self._on_reset)
        self.view.model.rowsInserted.connect(self._on_rows_inserted)

    def reset(self) -> None:
        """Clear all transaction data from the view."""
        self.view.model.clear()
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
        """Buffer incoming transactions and flush to the model."""
        self.view.set_end_date(event.date)
        for tx in event.transactions:
            if tx.id not in self._pushed_tx_ids:
                self.view.add_row(self._format_transaction(tx))
                self._pushed_tx_ids.add(tx.id)
                self._tx_count += 1
        self.view.flush_transactions()

    def _on_rows_inserted(self, _parent: QModelIndex, first: int, last: int) -> None:
        """Filter only newly inserted source rows when a filter is active."""
        if not self._filter_active:
            return
        proxy = self.view._sort_proxy  # noqa: SLF001
        for source_row in range(first, last + 1):
            if not self.view._source_row_matches_filter(source_row):  # noqa: SLF001
                proxy_idx = proxy.mapFromSource(self.view.model.index(source_row, 0))
                if proxy_idx.isValid():
                    self.view.table_view.setRowHidden(proxy_idx.row(), True)  # noqa: FBT003

    def _on_search(self) -> None:
        """Handle search button — apply filter and show indicator."""
        self._filter_active = True
        self.view.search_transactions()
        self.view.set_filter_indicator(active=True)

    def _on_reset(self) -> None:
        """Handle reset button — clear filter and hide indicator."""
        self._filter_active = False
        self.view.reset_filters()
        self.view.set_filter_indicator(active=False)

    def filter_by_instrument(self, instrument_id: str) -> None:
        """Set the instrument filter and trigger search."""
        self.view.instrument_filter.setText(instrument_id)
        self._on_search()

    def _on_context_menu(self, pos: object) -> None:
        """Show context menu for transaction history."""
        from PySide6.QtGui import QAction
        from PySide6.QtWidgets import QMenu

        from brms.app.clipboard import copy_tree_row, copy_tree_value

        table = self.view.table_view
        index = table.indexAt(pos)  # type: ignore[arg-type]
        if not index.isValid():
            return
        menu = QMenu(table)
        import qtawesome as qta
        copy_val = QAction(qta.icon("mdi6.content-copy"), "Copy Value", menu)
        copy_val.triggered.connect(lambda: copy_tree_value(table))
        menu.addAction(copy_val)
        copy_row_action = QAction("Copy Row", menu)
        copy_row_action.triggered.connect(lambda: copy_tree_row(table))
        menu.addAction(copy_row_action)
        copy_details = QAction("Copy All Details", menu)
        copy_details.triggered.connect(self._inspector_ctrl.copy_details)
        menu.addAction(copy_details)
        menu.exec(table.viewport().mapToGlobal(pos))  # type: ignore[arg-type]

    def _on_selection_changed(self) -> None:
        """Look up the selected transaction and show its details in the inspector."""
        indexes = self.view.table_view.selectedIndexes()
        if not indexes:
            return
        source_idx = self.view._sort_proxy.mapToSource(indexes[0])  # noqa: SLF001
        row_data = self.view.model.row_data(source_idx.row())
        tx_id = row_data[6]
        if not tx_id:
            return
        try:
            tx = self._transaction_log.get(tx_id)
        except KeyError:
            return
        self._inspector_ctrl.show_transaction_details(tx)

    def _format_transaction(self, transaction: Transaction) -> tuple:
        """Format a transaction as a tuple for the flat model."""
        type_label = transaction.type.name.replace("_", " ").title()
        description = transaction.description or type_label
        return (
            self._tx_count,
            str(transaction.date),
            type_label,
            transaction.instrument_id or "",
            float(transaction.amount),
            description,
            transaction.id,
        )
