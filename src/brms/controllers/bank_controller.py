from PySide6.QtCore import Signal

from brms.controllers.bank_book_controller import BankingBookController, TradingBookController
from brms.controllers.base import BRMSController
from brms.controllers.inspector_controller import InspectorController
from brms.models.bank import Bank
from brms.models.transaction import Action, BookType, Transaction
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
        self.banking_book_view.btn_test1.clicked.connect(self._test_deposit)  # test
        self.banking_book_view.btn_test2.clicked.connect(self._test_buy_htm_security)  # test

    def process_transaction(self, transaction: Transaction) -> None:
        """Process a transaction and emit signal."""
        # Let the bank (model) process the transaction
        self.bank.process_transaction(transaction)
        # Then emit the signal so that this controller can update related views
        self.transaction_processed.emit(transaction)

    def update_views(self, tx: Transaction) -> None:
        """Update the views based on the given transaction."""
        for instrument, (action, book_type, position) in tx.controller_actions().items():
            match (action, book_type, position):
                case (Action.ADD, BookType.BANKING_BOOK, _):
                    self.banking_book_ctrl.add_instrument(instrument, position)
                case (Action.ADD, BookType.TRADING_BOOK, _):
                    self.trading_book_ctrl.add_instrument(instrument, position)
                case (Action.REMOVE, BookType.BANKING_BOOK, _):
                    self.banking_book_ctrl.remove_instrument(instrument, position)
                case (Action.REMOVE, BookType.TRADING_BOOK, _):
                    self.trading_book_ctrl.remove_instrument(instrument, position)
                case (Action.UPDATE, BookType.BANKING_BOOK, _):
                    raise NotImplementedError
                case (Action.UPDATE, BookType.TRADING_BOOK, _):
                    raise NotImplementedError

    def _test(self) -> None:
        self._test_deposit()
        self._test_buy_htm_security()

    def _test_deposit(self) -> None:
        import datetime

        from brms.instruments.deposit import Deposit
        from brms.models.transaction import DepositTransaction

        today = datetime.date(2025, 1, 1)
        deposit = Deposit(value=10_000)
        tx = DepositTransaction(self.bank, deposit, today)
        self.process_transaction(tx)

    def _test_buy_htm_security(self) -> None:
        import QuantLib as ql

        from brms.instruments.base import BookType, CreditRating, Issuer, IssuerType
        from brms.instruments.fixed_rate_bond import FixedRateBond
        from brms.models.transaction import SecurityPurchaseHTMTransaction

        face_value = 5000.0
        coupon_rate = 0.05
        issue_date = ql.Date(1, 1, 2020)
        maturity_date = ql.Date(1, 1, 2030)
        bond = FixedRateBond(
            face_value=face_value,
            coupon_rate=coupon_rate,
            issue_date=issue_date,
            maturity_date=maturity_date,
            book_type=BookType.TRADING_BOOK,
            credit_rating=CreditRating.AA_MINUS,
            issuer=Issuer(
                name="Asian Development Bank",
                issuer_type=IssuerType.MDB,
                credit_rating=CreditRating.AA,
            ),
        )
        bond.value = face_value
        tx = SecurityPurchaseHTMTransaction(self.bank, bond, issue_date)
        self.process_transaction(tx)
