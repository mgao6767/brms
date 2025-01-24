from PySide6.QtCore import Signal

from brms.accounting.report import Report
from brms.accounting.statement_viewer import HTMLStatementViewer
from brms.controllers.bank_book_controller import BankingBookController, TradingBookController
from brms.controllers.base import BRMSController
from brms.controllers.inspector_controller import InspectorController
from brms.models.bank import Bank
from brms.models.transaction import Action, BookType, Transaction
from brms.views.bank_book_widget import BRMSBankingBookWidget, BRMSTradingBookWidget
from brms.views.statement_viewer_widget import BRMSStatementViewer


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
        statement_view: BRMSStatementViewer,
    ) -> None:
        super().__init__()
        self.bank = bank
        self.banking_book_view = banking_book_view
        self.trading_book_view = trading_book_view
        self.statement_view = statement_view
        # Controllers passed in
        self.inspector_ctrl = inspector_ctrl
        # Sub controllers
        # fmt: off
        self.banking_book_ctrl = BankingBookController(self.bank.banking_book, self.banking_book_view, self.inspector_ctrl)
        self.trading_book_ctrl = TradingBookController(self.bank.trading_book, self.trading_book_view, self.inspector_ctrl)
        # fmt: on
        # Connect signals
        self.connect_signals()

    def initialize_bank_from_transactions(self, transactions: list["Transaction"] | None = None) -> None:
        """Initialize the bank with a set of transactions.

        This method initializes both the bank's ledger and books with instruments.
        """
        transactions = transactions if transactions else []
        # Use bank.initialize_from_transactions because we want to start from a fresh financial period
        # The method closes the ledger
        self.bank.initialize_from_transactions(transactions)
        for transaction in transactions:
            self.transaction_processed.emit(transaction)

    def initialize_default_bank(self) -> None:
        """Initialize the bank with default transactions."""
        from brms.data.default import create_bank_init_transactions

        transactions = create_bank_init_transactions(self.bank)
        self.initialize_bank_from_transactions(transactions)

    def connect_signals(self) -> None:
        """Connect signals to their respective slots."""
        self.transaction_processed.connect(self.update_views)

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

    def update_statement(self) -> None:
        report = Report(
            self.bank.ledger,
            HTMLStatementViewer(
                console=False, padding=2, income_statement_table_width=80, balance_sheet_table_width=80
            ),
            self.bank.ledger.date_closed,
        )
        report.print_trial_balance()
        report.print_income_statement()
        report.print_balance_sheet()
        self.statement_view.trial_balance_browser.setHtml(report.trial_balance.html)
        self.statement_view.income_statement_browser.setHtml(report.income_statement.html)
        self.statement_view.balance_sheet_browser.setHtml(report.balance_sheet.html)

    def _test_init(self) -> None:
        self.initialize_default_bank()
        self.update_statement()

    def _test_buy_htm_security(self) -> None:
        import QuantLib as ql

        from brms.instruments.base import BookType, CreditRating, Issuer, IssuerType
        from brms.instruments.fixed_rate_bond import FixedRateBond
        from brms.models.transaction import TransactionFactory, TransactionType

        face_value = 5000.0
        coupon_rate = 0.05
        issue_date = ql.Date(1, 1, 2020)
        maturity_date = ql.Date(1, 1, 2030)
        bond = FixedRateBond(
            face_value=face_value,
            coupon_rate=coupon_rate,
            issue_date=issue_date,
            maturity_date=maturity_date,
            book_type=BookType.BANKING_BOOK,
            credit_rating=CreditRating.AA_MINUS,
            issuer=Issuer(
                name="Asian Development Bank",
                issuer_type=IssuerType.MDB,
                credit_rating=CreditRating.AA,
            ),
        )
        bond.value = face_value
        tx = TransactionFactory.create_transaction(
            bank=self.bank,
            transaction_type=TransactionType.SECURITY_PURCHASE_HTM,
            instrument=bond,
            transaction_date=issue_date,
        )
        self.process_transaction(tx)
        self.update_statement()
