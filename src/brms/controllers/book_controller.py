import QuantLib as ql
from PySide6.QtWidgets import QHeaderView

from brms.models.bank_banking_book_model import BankBankingBookModel
from brms.models.bank_trading_book_model import BankTradingBookModel
from brms.models.instruments import AmortizingFixedRateLoan, FixedRateBond, Instrument
from brms.views.bank_banking_book_widget import BankBankingBookWidget
from brms.views.bank_trading_book_widget import BankTradingBookWidget
from brms.views.base import TreeModel


class BookController:

    def __init__(
        self,
        model: BankBankingBookModel | BankTradingBookModel,
        view: BankBankingBookWidget | BankTradingBookWidget,
        assets_tree_view_header=["Asset", "Value"],
        liabilities_tree_view_header=["Liabilities & Equity", "Value"],
    ):
        self.model = model
        self.view = view
        self.assets_tree_view_header = assets_tree_view_header
        self.liabilities_tree_view_header = liabilities_tree_view_header

        self.model.asset_added.connect(self.update_assets_tree_view)
        self.model.liability_added.connect(self.update_liabilities_tree_view)

        self.update_assets_tree_view()
        self.update_liabilities_tree_view()

    def add_asset(self, instrument: Instrument):
        self.model.add_asset(instrument)

    def add_liability(self, instrument: Instrument):
        self.model.add_liability(instrument)

    def update_assets_tree_view(self):
        headers = self.assets_tree_view_header
        data = self.model.assets_data()
        self.view.assets_tree_view.setModel(TreeModel(headers, data))
        # fmt: off
        self.view.assets_tree_view.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.view.assets_tree_view.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.view.assets_tree_view.expandAll()
        # fmt: on

    def update_liabilities_tree_view(self):
        headers = self.liabilities_tree_view_header
        data = self.model.liabilities_data()
        self.view.liabilities_tree_view.setModel(TreeModel(headers, data))
        # fmt: off
        self.view.liabilities_tree_view.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.view.liabilities_tree_view.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.view.liabilities_tree_view.expandAll()
        # fmt: on

    def calculate_payments(self, prev_date: ql.Date, curr_date: ql.Date):

        for instrument in [*self.model.assets, *self.model.liabilities]:
            if isinstance(instrument, AmortizingFixedRateLoan):
                interest_pmt, principal_pmt, _ = instrument.payment_schedule()

                for pmt_date, pmt in interest_pmt:
                    if prev_date < pmt_date <= curr_date:
                        instrument.payments_received.emit(pmt)

                for pmt_date, pmt in principal_pmt:
                    if prev_date < pmt_date <= curr_date:
                        instrument.payments_received.emit(pmt)

            elif isinstance(instrument, FixedRateBond):
                payments = instrument.payment_schedule()

                for pmt_date, pmt in payments:
                    if prev_date < pmt_date <= curr_date:
                        instrument.payments_received.emit(pmt)


class TradingBookController(BookController):

    def __init__(
        self,
        model: BankTradingBookModel,
        view: BankTradingBookWidget,
        assets_tree_view_header=["Asset (Long)", "Value"],
        liabilities_tree_view_header=["Liability (Short)", "Value"],
    ):
        super().__init__(
            model, view, assets_tree_view_header, liabilities_tree_view_header
        )


class BankingBookController(BookController):

    def __init__(
        self,
        model: BankBankingBookModel,
        view: BankBankingBookWidget,
        assets_tree_view_header=["Asset", "Value"],
        liabilities_tree_view_header=["Liabilities & Equity", "Value"],
    ):
        super().__init__(
            model, view, assets_tree_view_header, liabilities_tree_view_header
        )

    def process_payments_received(self, payment):
        cash = self.model.get_cash()
        self.model.set_cash(cash + payment)

    def process_payments_paid(self, payment):
        cash = self.model.get_cash()
        self.model.set_cash(cash - payment)
