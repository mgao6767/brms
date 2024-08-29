from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGroupBox, QTreeView, QVBoxLayout, QWidget

from brms.views.base import BRMSSplitter, BRMSWidget, NumberFormatDelegate


class BankBookWidget(QWidget):

    def __init__(self, parent: QWidget | None = None, book_name: str = "") -> None:
        super().__init__(parent)
        self.book_name = book_name

        group_box = QGroupBox(book_name)
        self.assets_tree_view = QTreeView()
        self.liabilities_tree_view = QTreeView()
        self.assets_tree_view.setAlternatingRowColors(True)
        self.liabilities_tree_view.setAlternatingRowColors(True)
        self.num_delegate = NumberFormatDelegate()
        self.assets_tree_view.setItemDelegateForColumn(1, self.num_delegate)
        self.liabilities_tree_view.setItemDelegateForColumn(1, self.num_delegate)
        # Create a splitter to display the tree views side by side
        splitter = BRMSSplitter()
        splitter.addWidget(self.assets_tree_view)
        splitter.addWidget(self.liabilities_tree_view)

        # Create a layout for the widget and add the splitter
        layout = QVBoxLayout()
        layout.addWidget(splitter)

        group_box.setLayout(layout)

        book_layout = QVBoxLayout()
        book_layout.addWidget(group_box)
        self.setLayout(book_layout)


class BankBankingBookWidget(BankBookWidget):

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent, book_name="Banking Book")


class BankTradingBookWidget(BankBookWidget):

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent, book_name="Trading Book")


class BankBooksWidget(BRMSWidget):

    def __init__(self, parent: QWidget | None = None, f=Qt.WindowType.Window) -> None:
        super().__init__(parent, f)

        self.setWindowTitle("Banking and Trading Books")
        self.setGeometry(100, 100, 1024, 600)
        self.setMinimumSize(600, 500)

        self.bank_banking_book_widget = BankBankingBookWidget(self)
        self.bank_trading_book_widget = BankTradingBookWidget(self)

        splitter = BRMSSplitter()
        splitter.setContentsMargins(0, 0, 0, 0)
        splitter.setOrientation(Qt.Orientation.Horizontal)
        splitter.addWidget(self.bank_banking_book_widget)
        splitter.addWidget(self.bank_trading_book_widget)

        layout = QVBoxLayout()
        layout.addWidget(splitter)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        self.center_window()
