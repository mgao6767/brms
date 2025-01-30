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
        self.transaction_tree = BRMSTreeWidget(["Tx#", "Date", "Type", "Instrument", "Value", "Description"])
        self.transaction_tree.header().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.transaction_tree.setUniformRowHeights(True)  # for performance
        self.transaction_tree.setItemDelegateForColumn(4, CurrencyDelegate(self.transaction_tree))  # value column

        # Convenient access
        self.transactions_tree_model = self.transaction_tree.tree_model

        # Arrange in a splitter
        splitter = QSplitter()
        splitter.addWidget(self.ctrl_group)
        splitter.addWidget(self.transaction_tree)
        splitter.setStretchFactor(1, 1)

        # Main layout
        main_layout = QHBoxLayout()
        main_layout.addWidget(splitter)
        self.setLayout(main_layout)

        # Connect signals
        self.reset_button.clicked.connect(self.reset_filters)

    def set_start_date(self, date: QDate | datetime.date) -> None:
        self.start_date_filter.setDate(pydate_to_qdate(date) if isinstance(date, datetime.date) else date)

    def set_end_date(self, date: QDate | datetime.date) -> None:
        self.end_date_filter.setDate(pydate_to_qdate(date) if isinstance(date, datetime.date) else date)

    def reset_filters(self) -> None:
        pass

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
        }
