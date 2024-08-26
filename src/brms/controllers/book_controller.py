import QuantLib as ql
from PySide6.QtWidgets import QHeaderView

from brms.controllers.base import BRMSController
from brms.models.bank_book_model import BankBankingBookModel, BankTradingBookModel
from brms.models.instruments import AmortizingFixedRateLoan, FixedRateBond, Instrument
from brms.views.bank_book_widget import BankBankingBookWidget, BankTradingBookWidget
from brms.views.base import TreeModel


class BookController(BRMSController):

    def __init__(
        self,
        model: BankBankingBookModel | BankTradingBookModel,
        view: BankBankingBookWidget | BankTradingBookWidget,
        assets_tree_view_header=["Asset", "Value"],
        liabilities_tree_view_header=["Liabilities & Equity", "Value"],
    ):
        super().__init__()
        self.model = model
        self.view = view
        self.assets_tree_model = None
        self.liabilities_tree_model = None
        self.assets_tree_view_header = assets_tree_view_header
        self.liabilities_tree_view_header = liabilities_tree_view_header

        self.model.asset_added.connect(self.update_assets_tree_view)
        self.model.liability_added.connect(self.update_liabilities_tree_view)

        self.update_assets_tree_view()
        self.update_liabilities_tree_view()

    def reset(self):
        self.model.reset()
        self.update_assets_tree_view()
        self.update_liabilities_tree_view()

    def expand_all_tree_view(self):
        self.view.assets_tree_view.expandAll()
        self.view.liabilities_tree_view.expandAll()

    def add_asset(self, instrument: Instrument):
        self.model.add_asset(instrument)

    def add_liability(self, instrument: Instrument):
        self.model.add_liability(instrument)

    def get_expanded_item_indices(self, model, tree_view):
        if not model:
            return []
        expanded_indices = (
            model.index(index, 0)
            for index in range(model.rowCount())
            if tree_view.isExpanded(model.index(index, 0))
        )
        return [(index.row(), index.column()) for index in expanded_indices]

    def expand_tree_view_items(self, item_indices, model, tree_view):
        for row, column in item_indices:
            new_index = model.index(row, column)
            tree_view.expand(new_index)

    def set_tree_view_header_resize_mode(self, tree_view):
        tree_view.header().setSectionResizeMode(0, QHeaderView.Stretch)
        tree_view.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)

    def update_assets_tree_view(self):
        data = self.model.assets_data()
        headers = self.assets_tree_view_header
        tree_view = self.view.assets_tree_view
        old_model = self.assets_tree_model
        new_model = TreeModel(headers, data)

        expanded_indices = self.get_expanded_item_indices(old_model, tree_view)
        tree_view.setModel(new_model)
        self.assets_tree_model = new_model
        self.expand_tree_view_items(expanded_indices, new_model, tree_view)
        self.set_tree_view_header_resize_mode(tree_view)

    def update_liabilities_tree_view(self):
        data = self.model.liabilities_data()
        headers = self.liabilities_tree_view_header
        tree_view = self.view.liabilities_tree_view
        old_model = self.liabilities_tree_model
        new_model = TreeModel(headers, data)

        expanded_indices = self.get_expanded_item_indices(old_model, tree_view)
        tree_view.setModel(new_model)
        self.liabilities_tree_model = new_model
        self.expand_tree_view_items(expanded_indices, new_model, tree_view)
        self.set_tree_view_header_resize_mode(tree_view)

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
