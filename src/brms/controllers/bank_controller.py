import datetime

from PySide6.QtCore import Signal

from brms.accounting.report import Report
from brms.accounting.statement_viewer import HTMLStatementViewer
from brms.controllers.bank_book_controller import BankingBookController, TradingBookController
from brms.controllers.base import BRMSController
from brms.controllers.inspector_controller import InspectorController
from brms.data.default import create_bank_init_transactions
from brms.models.bank import Bank
from brms.models.scenario import ScenarioManager
from brms.models.transaction import Action, BookType, Transaction
from brms.views.bank_book_widget import BRMSBankingBookWidget, BRMSTradingBookWidget
from brms.views.statement_viewer_widget import BRMSStatementViewer


class BankController(BRMSController):
    """Controller for managing bank operations, including banking and trading books.

    The bank controller should only modify the state of the bank model through `Transaction`.
    After transactions have been processed, the controller sync the state of the bank model and those for various views.
    """

    transaction_processed = Signal(Transaction, name="Transaction Processed")
    bank_financials_updated = Signal(Report, name="Bank Financials Updated")

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
        self.report: Report
        self.total_assets_history: dict[datetime.date, float] = {}
        self.total_liabilities_history: dict[datetime.date, float] = {}
        self.total_equity_history: dict[datetime.date, float] = {}
        # Controllers passed in
        self.inspector_ctrl = inspector_ctrl
        # Sub controllers
        # fmt: off
        self.banking_book_ctrl = BankingBookController(self.bank.banking_book, self.banking_book_view, self.inspector_ctrl)
        self.trading_book_ctrl = TradingBookController(self.bank.trading_book, self.trading_book_view, self.inspector_ctrl)
        # fmt: on
        # Connect signals
        self.connect_signals()

    def init(self, scenario_manager: ScenarioManager) -> None:
        """Initialize the bank with default transactions."""
        for tx in create_bank_init_transactions(self.bank, scenario_manager):
            if self.bank.process_transaction(tx):
                self.transaction_processed.emit(tx)

    def connect_signals(self) -> None:
        """Connect signals to their respective slots."""
        self.transaction_processed.connect(self.update_views)

    def process_transaction(self, transaction: Transaction) -> None:
        """Process a transaction and emit signal."""
        # Let the bank (model) process the transaction
        if self.bank.process_transaction(transaction):
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
                    self.banking_book_ctrl.update_instrument(instrument, position)
                case (Action.UPDATE, BookType.TRADING_BOOK, _):
                    self.trading_book_ctrl.update_instrument(instrument, position)

    def update_statement(self, date: datetime.date | None = None) -> None:
        self.report = Report(
            ledger=self.bank.ledger,
            viewer=HTMLStatementViewer(
                console=False,
                padding=2,
                income_statement_table_width=80,
                balance_sheet_table_width=80,
            ),
            date=date or self.bank.ledger.date_closed,
        )
        self.report.print_trial_balance()
        self.report.print_income_statement()
        self.report.print_balance_sheet()
        # Save current scroll positions
        trial_balance_v_scroll_pos = self.statement_view.trial_balance_browser.verticalScrollBar().value()
        trial_balance_h_scroll_pos = self.statement_view.trial_balance_browser.horizontalScrollBar().value()
        income_statement_v_scroll_pos = self.statement_view.income_statement_browser.verticalScrollBar().value()
        income_statement_h_scroll_pos = self.statement_view.income_statement_browser.horizontalScrollBar().value()
        balance_sheet_v_scroll_pos = self.statement_view.balance_sheet_browser.verticalScrollBar().value()
        balance_sheet_h_scroll_pos = self.statement_view.balance_sheet_browser.horizontalScrollBar().value()
        # Set new HTML content
        self.statement_view.trial_balance_browser.setHtml(self.report.trial_balance.html)
        self.statement_view.income_statement_browser.setHtml(self.report.income_statement.html)
        self.statement_view.balance_sheet_browser.setHtml(self.report.balance_sheet.html)
        # Restore scroll positions
        self.statement_view.trial_balance_browser.verticalScrollBar().setValue(trial_balance_v_scroll_pos)
        self.statement_view.trial_balance_browser.horizontalScrollBar().setValue(trial_balance_h_scroll_pos)
        self.statement_view.income_statement_browser.verticalScrollBar().setValue(income_statement_v_scroll_pos)
        self.statement_view.income_statement_browser.horizontalScrollBar().setValue(income_statement_h_scroll_pos)
        self.statement_view.balance_sheet_browser.verticalScrollBar().setValue(balance_sheet_v_scroll_pos)
        self.statement_view.balance_sheet_browser.horizontalScrollBar().setValue(balance_sheet_h_scroll_pos)

        # Update the financial metrics and emit signals
        if date is not None:
            self.total_assets_history[date] = self.report.get_total_assets()
            self.total_liabilities_history[date] = self.report.get_total_liabilities()
            self.total_equity_history[date] = self.report.get_total_equity()

            self.bank_financials_updated.emit(self.report)
