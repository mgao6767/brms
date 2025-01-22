from PySide6.QtCore import Signal

from brms.controllers.bank_book_controller import BankingBookController, TradingBookController
from brms.controllers.base import BRMSController
from brms.controllers.inspector_controller import InspectorController
from brms.models.bank import Bank
from brms.models.transaction import Transaction
from brms.views.bank_book_widget import BRMSBankingBookWidget, BRMSTradingBookWidget


class BankController(BRMSController):
    """Controller for managing bank operations, including banking and trading books.

    The bank controller should only modify the state of the bank model through `Transaction`.
    After transactions have been processed, the controller sync the state of the bank model and those for various views.
    """

    transaction_processed = Signal(Transaction, name="Transaction Processed")

    def __init__(
        self,
        bank: Bank,
        banking_book_view: BRMSBankingBookWidget,
        trading_book_view: BRMSTradingBookWidget,
        inspector_ctrl: InspectorController,
    ) -> None:
        super().__init__()
        self.bank = bank
        self.banking_book_view = banking_book_view
        self.trading_book_view = trading_book_view
        # Controllers passed in
        self.inspector_ctrl = inspector_ctrl
        # Sub controllers
        # fmt: off
        self.banking_book_ctrl = BankingBookController(self.bank.banking_book, self.banking_book_view, self.inspector_ctrl)
        self.trading_book_ctrl = TradingBookController(self.bank.trading_book, self.trading_book_view, self.inspector_ctrl)
        # fmt: on
        # Connect signals
        self.connect_signals()

    def connect_signals(self) -> None:
        """Connect signals to their respective slots."""
        self.transaction_processed.connect(self.update_views)
        self.banking_book_view.btn_test.clicked.connect(self._test)  # test

    def process_transaction(self, transaction: Transaction) -> None:
        """Process a transaction and emit signal."""
        # Let the bank (model) process the transaction
        self.bank.process_transaction(transaction)
        # Then emit the signal so that this controller can update related views
        self.transaction_processed.emit(transaction)

    def update_views(self, tx: Transaction) -> None:
        """Update the views based on the given transaction."""

    def _test(self) -> None:
        print("Test button pressed.")
