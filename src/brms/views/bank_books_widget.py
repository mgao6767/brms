from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout, QWidget

from brms.views.bank_banking_book_widget import BankBankingBookWidget
from brms.views.bank_trading_book_widget import BankTradingBookWidget
from brms.views.base import CustomSplitter, CustomWidget


class BankBooksWidget(CustomWidget):

    def __init__(self, parent: QWidget | None = ..., f = Qt.WindowType.Window) -> None:
        super().__init__(parent, f)

        self.setWindowTitle("Banking and Trading Books")
        self.setGeometry(100, 100, 1024, 600)
        self.setMinimumSize(600, 500)

        self.bank_banking_book_widget = BankBankingBookWidget(self)
        self.bank_trading_book_widget = BankTradingBookWidget(self)

        splitter = CustomSplitter()
        splitter.setOrientation(Qt.Orientation.Horizontal)
        splitter.addWidget(self.bank_banking_book_widget)
        splitter.addWidget(self.bank_trading_book_widget)

        layout = QVBoxLayout()
        layout.addWidget(splitter)
        self.setLayout(layout)

        self.center_window()