import datetime

from PySide6.QtCore import QDate, QLocale, Qt, QTimer
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from brms.models.transaction import Transaction, TransactionFactory
from brms.utils import pydate_to_qdate
from brms.views.bank_book_widget import CurrencyDelegate
from brms.views.tree_widget import QMODELINDEX, BRMSTreeWidget


class BRMSTransactionHistoryWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.tx_count = 0
        # For performance
        self._transaction_buffer = []
        self._transaction_buffer_max_size = 100
        self._transaction_timer = QTimer(self)
        self._transaction_timer.setInterval(200)
        self._transaction_timer.timeout.connect(self.flush_transactions)
        self._transaction_timer.start()
        self._locale = QLocale()

        # Create a group box for journal entry
        self.journal_group = QGroupBox("Journal Entry")
        journal_layout = QVBoxLayout()
        self.journal_display = QLabel("")
        self.journal_display.setTextFormat(Qt.TextFormat.RichText)
        journal_layout.addWidget(self.journal_display)
        self.journal_group.setLayout(journal_layout)
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
        self.type_filter.addItem("All")
        for tx_type in TransactionFactory.get_registered_transaction_types():
            self.type_filter.addItem(tx_type.name)
        self.search_button = QPushButton("Search")
        self.reset_button = QPushButton("Reset")

        # Add widgets to layout
        group_layout.addWidget(self.start_date_label)
        group_layout.addWidget(self.start_date_filter)
        group_layout.addWidget(self.end_date_label)
        group_layout.addWidget(self.end_date_filter)
        group_layout.addWidget(self.type_label)
        group_layout.addWidget(self.type_filter)
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

        # Arrange in a splitter
        left_widget = QSplitter()
        left_widget.setOrientation(Qt.Orientation.Vertical)
        left_widget.addWidget(self.journal_group)
        left_widget.addWidget(self.ctrl_group)
        left_widget.setStretchFactor(0, 0)
        left_widget.setStretchFactor(1, 2)
        splitter = QSplitter()
        splitter.addWidget(left_widget)
        splitter.addWidget(self.transaction_tree)
        splitter.setStretchFactor(1, 1)

        # Main layout
        main_layout = QHBoxLayout()
        main_layout.addWidget(splitter)
        self.setLayout(main_layout)

        # Connect signals
        self.search_button.clicked.connect(self.search_transactions)
        self.reset_button.clicked.connect(self.reset_filters)
        self.start_date_filter.dateChanged.connect(self.validate_dates)
        self.end_date_filter.dateChanged.connect(self.validate_dates)
        self.transaction_tree.selectionModel().selectionChanged.connect(self.on_transaction_selected)

    def validate_dates(self):
        """Ensure start date is earlier than or equal to end date."""
        start_date = self.start_date_filter.date()
        end_date = self.end_date_filter.date()
        if start_date > end_date:
            self.start_date_filter.setDate(end_date)  # Reset start date to match end date

    def on_transaction_selected(self, selected, deselected) -> None:
        """Slot to handle selection changes."""
        indexes = self.transaction_tree.selectedIndexes()
        id_column = 6  # journal entry
        if indexes:
            selected_index = indexes[0]
            item = selected_index.internalPointer()
            entry = item.data(id_column)
            self.journal_display.setText(entry.to_html())

    def search_transactions(self) -> None:
        self.reset_filters()
        start_date = self.start_date_filter.date().toPython()
        end_date = self.end_date_filter.date().toPython()
        tx_type = self.type_filter.currentText()
        model = self.transactions_tree_model
        for row in range(model.rowCount()):
            idx_date = model.index(row, 1, QMODELINDEX)  # date
            idx_tx_type = model.index(row, 2, QMODELINDEX)  # transaction type
            if not (idx_date.isValid() and idx_tx_type.isValid()):
                continue
            date_text = model.data(idx_date, Qt.ItemDataRole.DisplayRole)
            tx_type_text = model.data(idx_tx_type, Qt.ItemDataRole.DisplayRole)
            date = datetime.datetime.strptime(date_text, "%Y-%m-%d").date()
            if start_date <= date <= end_date and (tx_type == "All" or tx_type_text == tx_type):
                self.transaction_tree.setRowHidden(row, QMODELINDEX, False)
            else:
                self.transaction_tree.setRowHidden(row, QMODELINDEX, True)

    def reset_filters(self) -> None:
        for row in range(self.transactions_tree_model.rowCount()):
            self.transaction_tree.setRowHidden(row, QMODELINDEX, False)

    def set_start_date(self, date: QDate | datetime.date) -> None:
        self.start_date_filter.setDate(pydate_to_qdate(date) if isinstance(date, datetime.date) else date)

    def set_end_date(self, date: QDate | datetime.date) -> None:
        self.end_date_filter.setDate(pydate_to_qdate(date) if isinstance(date, datetime.date) else date)

    def flush_transactions(self):
        if not self._transaction_buffer:
            return
        data = [self.transaction_to_data(tx, self.tx_count + i) for i, tx in enumerate(self._transaction_buffer)]
        self.tx_count += len(self._transaction_buffer)
        self.setUpdatesEnabled(False)
        self.transactions_tree_model.layoutAboutToBeChanged.emit()
        self.transactions_tree_model.blockSignals(True)
        self.transactions_tree_model.add_data(QMODELINDEX, data)
        self.transactions_tree_model.blockSignals(False)
        self.transactions_tree_model.layoutChanged.emit()
        self._transaction_buffer.clear()
        self.transaction_tree.scrollToBottom()
        self.setUpdatesEnabled(True)

    def add_transaction(self, transaction: Transaction) -> None:
        self._transaction_buffer.append(transaction)
        if len(self._transaction_buffer) >= self._transaction_buffer_max_size:
            self.flush_transactions()

    def transaction_to_data(self, transaction: Transaction, tx_num: int) -> dict:
        return {
            0: tx_num,
            1: str(transaction.transaction_date),
            2: transaction.transaction_type.name,
            3: transaction.instrument.name,
            4: self._locale.toCurrencyString(transaction.value),
            5: transaction.description,
            # hidden
            6: transaction.journal_entry,
        }
