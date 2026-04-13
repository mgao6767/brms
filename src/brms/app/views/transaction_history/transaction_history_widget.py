import datetime

from PySide6.QtCore import QDate, Qt, QTimer
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from brms.app.utils import pydate_to_qdate
from brms.app.views.bank_book.delegates import CurrencyDelegate
from brms.app.views.widgets.tree_widget import QMODELINDEX, BRMSTreeWidget

CONTROL_PANEL_WIDTH = 220


class BRMSTransactionHistoryWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        # For performance
        self._transaction_buffer: list[dict] = []
        self._transaction_buffer_max_size = 100
        self._transaction_timer = QTimer(self)
        self._transaction_timer.setInterval(200)
        self._transaction_timer.timeout.connect(self.flush_transactions)
        self._transaction_timer.start()
        # Create a control panel
        self.ctrl_group = QGroupBox("Filter")
        group_layout = QVBoxLayout()
        group_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        # Add filter controls
        self.start_date_label = QLabel("Start Date:")
        self.start_date_filter = QDateEdit()
        self.end_date_label = QLabel("End Date:")
        self.end_date_filter = QDateEdit()
        self.type_label = QLabel("Transaction Type:")
        self.type_filter = QComboBox()
        self.instrument_label = QLabel("Instrument ID:")
        self.instrument_filter = QLineEdit()
        self.instrument_filter.setPlaceholderText("Partial match…")
        self.search_button = QPushButton("Search")
        self.reset_button = QPushButton("Reset")

        # Add widgets to layout
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

        # Create a tree view
        columns = ["Tx#", "Date", "Type", "Instrument", "Value", "Description", "Journal Entry"]
        self.transaction_tree = BRMSTreeWidget(columns)
        self.transaction_tree.header().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.transaction_tree.setUniformRowHeights(True)  # for performance
        self.transaction_tree.setItemDelegateForColumn(4, CurrencyDelegate(self.transaction_tree))  # value column
        self.transaction_tree.setColumnHidden(6, True)  # journal entry

        # Convenient access
        self.transactions_tree_model = self.transaction_tree.tree_model

        # Arrange in a splitter with fixed-width left panel
        self.ctrl_group.setFixedWidth(CONTROL_PANEL_WIDTH)
        splitter = QSplitter()
        splitter.addWidget(self.ctrl_group)
        splitter.addWidget(self.transaction_tree)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        # Main layout
        main_layout = QHBoxLayout()
        main_layout.addWidget(splitter)
        self.setLayout(main_layout)

        # Filter active indicator
        self._filter_group_default_title = "Filter"

        # Connect signals (date validation only — search/reset owned by controller)
        self.start_date_filter.dateChanged.connect(self.validate_dates)
        self.end_date_filter.dateChanged.connect(self.validate_dates)

    def validate_dates(self):
        """Ensure start date is earlier than or equal to end date."""
        start_date = self.start_date_filter.date()
        end_date = self.end_date_filter.date()
        if start_date > end_date:
            self.start_date_filter.setDate(end_date)  # Reset start date to match end date

    def search_transactions(self) -> None:
        self.reset_filters()
        start_date = self.start_date_filter.date().toPython()
        end_date = self.end_date_filter.date().toPython()
        tx_type = self.type_filter.currentText()
        instrument_query = self.instrument_filter.text().strip().lower()
        model = self.transactions_tree_model
        for row in range(model.rowCount()):
            idx_date = model.index(row, 1, QMODELINDEX)  # date
            idx_tx_type = model.index(row, 2, QMODELINDEX)  # transaction type
            idx_instrument = model.index(row, 3, QMODELINDEX)  # instrument id
            if not (idx_date.isValid() and idx_tx_type.isValid()):
                continue
            date_text = model.data(idx_date, Qt.ItemDataRole.DisplayRole)
            tx_type_text = model.data(idx_tx_type, Qt.ItemDataRole.DisplayRole)
            date = datetime.datetime.strptime(date_text, "%Y-%m-%d").date()
            date_ok = start_date <= date <= end_date
            type_ok = tx_type == "All" or tx_type_text == tx_type
            if instrument_query:
                inst_text = str(model.data(idx_instrument, Qt.ItemDataRole.DisplayRole) or "").lower()
                inst_ok = instrument_query in inst_text
            else:
                inst_ok = True
            self.transaction_tree.setRowHidden(row, QMODELINDEX, not (date_ok and type_ok and inst_ok))

    def reset_filters(self) -> None:
        for row in range(self.transactions_tree_model.rowCount()):
            self.transaction_tree.setRowHidden(row, QMODELINDEX, False)

    def set_start_date(self, date: QDate | datetime.date) -> None:
        self.start_date_filter.setDate(pydate_to_qdate(date) if isinstance(date, datetime.date) else date)

    def set_end_date(self, date: QDate | datetime.date) -> None:
        self.end_date_filter.setDate(pydate_to_qdate(date) if isinstance(date, datetime.date) else date)

    def set_filter_indicator(self, *, active: bool) -> None:
        """Show or hide a visual indicator that filters are active."""
        if active:
            self.ctrl_group.setTitle("Filter (active)")
            self.ctrl_group.setStyleSheet("QGroupBox { color: #e67e22; font-weight: bold; }")
        else:
            self.ctrl_group.setTitle(self._filter_group_default_title)
            self.ctrl_group.setStyleSheet("")

    def flush_transactions(self) -> None:
        """Flush buffered row dicts to the tree model."""
        if not self._transaction_buffer:
            return
        self.setUpdatesEnabled(False)
        self.transactions_tree_model.layoutAboutToBeChanged.emit()
        self.transactions_tree_model.blockSignals(True)
        self.transactions_tree_model.add_data(QMODELINDEX, list(self._transaction_buffer))
        self.transactions_tree_model.blockSignals(False)
        self.transactions_tree_model.layoutChanged.emit()
        self._transaction_buffer.clear()
        self.transaction_tree.scrollToBottom()
        self.setUpdatesEnabled(True)

    def add_row(self, row_data: dict) -> None:
        """Buffer a pre-formatted row dict for batch insertion."""
        self._transaction_buffer.append(row_data)
        if len(self._transaction_buffer) >= self._transaction_buffer_max_size:
            self.flush_transactions()
