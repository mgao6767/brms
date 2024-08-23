from collections import defaultdict

import QuantLib as ql
from PySide6.QtWidgets import QHeaderView

from brms.models.bank_trading_book_model import BankTradingBookModel
from brms.models.instruments import Instrument
from brms.views.bank_trading_book_widget import BankTradingBookWidget
from brms.views.base import TreeModel


class TradingBookController:

    def __init__(self, model: BankTradingBookModel, view: BankTradingBookWidget):
        self.model = model
        self.view = view

        self.model.asset_added.connect(self.update_assets_tree_view)
        self.model.liability_added.connect(self.update_liabilities_tree_view)

        self.update_assets_tree_view()
        self.update_liabilities_tree_view()

    def add_asset(self, instrument: Instrument):

        self.model.add_asset(instrument)

    def remove_asset(self):
        pass

    def add_liability(self, instrument: Instrument):

        self.model.add_liability(instrument)

    def remove_liability(self):
        pass

    def update_assets_tree_view(self):
        headers = ["Asset (Long)", "Value"]
        data = self.model.assets_data()
        self.view.assets_tree_view.setModel(TreeModel(headers, data))
        # fmt: off
        self.view.assets_tree_view.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.view.assets_tree_view.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.view.assets_tree_view.expandAll()
        # fmt: on

    def update_liabilities_tree_view(self):
        headers = ["Liability (Short)", "Value"]
        data = self.model.liabilities_data()
        self.view.liabilities_tree_view.setModel(TreeModel(headers, data))
        # fmt: off
        self.view.liabilities_tree_view.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.view.liabilities_tree_view.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.view.liabilities_tree_view.expandAll()
        # fmt: on
