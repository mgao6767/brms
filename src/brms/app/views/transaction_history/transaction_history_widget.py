"""Transaction history widget — QTableView backed by a flat list model."""

from __future__ import annotations

import datetime

from PySide6.QtCore import QDate, QSortFilterProxyModel, Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDateEdit,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from brms.app.models.transaction_table_model import TransactionTableModel
from brms.app.utils import pydate_to_qdate
from brms.app.views.bank_book.delegates import CurrencyDelegate
from brms.app.views.styler import BRMSStyler

CONTROL_PANEL_WIDTH = 220
_COL_VALUE = 4
_COL_ID = 6


class BRMSTransactionHistoryWidget(QWidget):
    """Transaction history view with filter panel and flat table."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the transaction history widget."""
        super().__init__(parent)

        self._transaction_buffer: list[tuple] = []

        # Filter panel
        self.ctrl_group = QGroupBox("Filter")
        group_layout = QVBoxLayout()
        group_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.start_date_label = QLabel("Start Date:")
        self.start_date_filter = QDateEdit()
        self.end_date_label = QLabel("End Date:")
        self.end_date_filter = QDateEdit()
        self.type_label = QLabel("Transaction Type:")
        self.type_filter = QComboBox()
        self.instrument_label = QLabel("Instrument ID:")
        self.instrument_filter = QLineEdit()
        self.instrument_filter.setPlaceholderText("Partial match\u2026")
        self.search_button = QPushButton("Search")
        self.reset_button = QPushButton("Reset")

        group_layout.addWidget(self.start_date_label)
        group_layout.addWidget(self.start_date_filter)
        group_layout.addWidget(self.end_date_label)
        group_layout.addWidget(self.end_date_filter)
        group_layout.addWidget(self.type_label)
        group_layout.addWidget(self.type_filter)
        group_layout.addWidget(self.instrument_label)
        group_layout.addWidget(self.instrument_filter)
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.NoFrame)
        group_layout.addWidget(separator)
        group_layout.addWidget(self.search_button)
        group_layout.addWidget(self.reset_button)
        self.ctrl_group.setLayout(group_layout)

        # Table model + sort proxy (dynamicSort off — only sorts on header click)
        self.model = TransactionTableModel(self)
        self._sort_proxy = QSortFilterProxyModel(self)
        self._sort_proxy.setSourceModel(self.model)
        self._sort_proxy.setDynamicSortFilter(False)

        self.table_view = QTableView(self)
        self.table_view.setModel(self._sort_proxy)
        self.table_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_view.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table_view.setAlternatingRowColors(False)
        self.table_view.setShowGrid(False)
        self.table_view.setSortingEnabled(True)
        self.table_view.verticalHeader().setVisible(False)
        self.table_view.verticalHeader().setMinimumSectionSize(4)
        self.table_view.verticalHeader().setDefaultSectionSize(self.fontMetrics().height() + 6)
        self.table_view.horizontalHeader().setStretchLastSection(True)
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table_view.setItemDelegateForColumn(_COL_VALUE, CurrencyDelegate(self.table_view))
        self.table_view.setColumnHidden(_COL_ID, True)

        # Layout — QHBoxLayout with spacing (matches RWA tab pattern)
        self.ctrl_group.setFixedWidth(CONTROL_PANEL_WIDTH)
        main_layout = QHBoxLayout()
        main_layout.addWidget(self.ctrl_group)
        main_layout.addWidget(self.table_view, stretch=1)
        self.setLayout(main_layout)

        self._filter_group_default_title = "Filter"
        self.start_date_filter.dateChanged.connect(self._validate_dates)
        self.end_date_filter.dateChanged.connect(self._validate_dates)

    def _validate_dates(self) -> None:
        """Ensure start date is earlier than or equal to end date."""
        if self.start_date_filter.date() > self.end_date_filter.date():
            self.start_date_filter.setDate(self.end_date_filter.date())

    # -- Filter helpers ---------------------------------------------------

    def _source_row_matches_filter(self, source_row: int) -> bool:
        """Check whether a source model row matches the current filter controls."""
        row_data = self.model.row_data(source_row)
        start_date = self.start_date_filter.date().toPython()
        end_date = self.end_date_filter.date().toPython()
        tx_type = self.type_filter.currentText()
        instrument_query = self.instrument_filter.text().strip().lower()

        date = datetime.date.fromisoformat(str(row_data[1]))
        if not (start_date <= date <= end_date):
            return False
        if tx_type != "All" and row_data[2] != tx_type:
            return False
        return not (instrument_query and instrument_query not in str(row_data[3]).lower())

    def search_transactions(self) -> None:
        """Apply filter controls to all rows (operates on proxy row indices)."""
        self.reset_filters()
        proxy = self._sort_proxy
        for proxy_row in range(proxy.rowCount()):
            source_row = proxy.mapToSource(proxy.index(proxy_row, 0)).row()
            if not self._source_row_matches_filter(source_row):
                self.table_view.setRowHidden(proxy_row, True)  # noqa: FBT003

    def reset_filters(self) -> None:
        """Unhide all rows and restore insertion order (Tx# ascending)."""
        self._sort_proxy.sort(0, Qt.SortOrder.AscendingOrder)
        for row in range(self._sort_proxy.rowCount()):
            self.table_view.setRowHidden(row, False)  # noqa: FBT003
        self.table_view.horizontalHeader().setSortIndicator(-1, Qt.SortOrder.AscendingOrder)

    # -- Public API -------------------------------------------------------

    def set_start_date(self, date: QDate | datetime.date) -> None:
        """Set the start date filter."""
        self.start_date_filter.setDate(pydate_to_qdate(date) if isinstance(date, datetime.date) else date)

    def set_end_date(self, date: QDate | datetime.date) -> None:
        """Set the end date filter."""
        self.end_date_filter.setDate(pydate_to_qdate(date) if isinstance(date, datetime.date) else date)

    def set_filter_indicator(self, *, active: bool) -> None:
        """Show or hide a visual indicator that filters are active."""
        if active:
            styler = BRMSStyler.instance()
            self.ctrl_group.setTitle("Filter (active)")
            self.ctrl_group.setStyleSheet(
                f"QGroupBox {{ color: {styler.interactive_hover}; font-weight: 600; }}",
            )
        else:
            self.ctrl_group.setTitle(self._filter_group_default_title)
            self.ctrl_group.setStyleSheet("")

    def add_row(self, row_tuple: tuple) -> None:
        """Buffer a row tuple for batch insertion."""
        self._transaction_buffer.append(row_tuple)

    def flush_transactions(self) -> None:
        """Flush buffered rows to the model in a single insert."""
        if not self._transaction_buffer:
            return
        needs_initial_sort = self.model.rowCount() == 0
        self.table_view.setUpdatesEnabled(False)
        self.model.append_rows(list(self._transaction_buffer))
        self._transaction_buffer.clear()
        if needs_initial_sort:
            self._sort_proxy.sort(0, Qt.SortOrder.AscendingOrder)
        self.table_view.scrollToBottom()
        self.table_view.setUpdatesEnabled(True)
