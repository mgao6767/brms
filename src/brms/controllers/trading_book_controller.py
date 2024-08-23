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
        grouped_assets = defaultdict(lambda: defaultdict(list))

        # Group assets by class type and name
        for asset in self.model.assets:
            grouped_assets[type(asset).instrument_type][asset.name].append(asset)

        eval_date = ql.Settings.instance().evaluationDate

        # Create the data structure for the tree view
        data = []
        # Each asset_type is like Cash, Loans, etc
        for asset_type, assets_by_name in grouped_assets.items():
            asset_type_val = 0.0
            asset_type_data = {"data": [asset_type, asset_type_val], "children": []}
            # Each asset within a type represents a specific asset
            for name, assets in assets_by_name.items():
                total_value = sum(a.value_on_trading_book(eval_date) for a in assets)
                asset_type_val += total_value
                asset_type_data["children"].append({"data": [name, total_value]})

            asset_type_data["data"] = [asset_type, asset_type_val]
            data.append(asset_type_data)

        self.view.assets_tree_view.setModel(TreeModel(headers, data))

        # fmt: off
        self.view.assets_tree_view.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.view.assets_tree_view.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.view.assets_tree_view.expandAll()
        # fmt: on

    def update_liabilities_tree_view(self):
        headers = ["Liability (Short)", "Value"]
        grouped_liabilities = defaultdict(lambda: defaultdict(list))

        # Group liabilities by class type and name
        # fmt: off
        for liability in self.model.liabilities:
            grouped_liabilities[type(liability).instrument_type][liability.name].append(liability)

        eval_date = ql.Settings.instance().evaluationDate

        # Create the data structure for the tree view
        data = []
        # Each liability_type is like Loans, Mortgages, etc
        for liability_type, liabilities_by_name in grouped_liabilities.items():
            liability_type_val = 0.0
            liability_type_data = {
                "data": [liability_type, liability_type_val],
                "children": [],
            }
            # Each liability within a type represents a specific liability
            for name, liabilities in liabilities_by_name.items():
                total_value = sum(l.value_on_trading_book(eval_date) for l in liabilities)
                liability_type_val += total_value
                liability_type_data["children"].append({"data": [name, total_value]})

            liability_type_data["data"] = [liability_type, liability_type_val]
            data.append(liability_type_data)

        self.view.liabilities_tree_view.setModel(TreeModel(headers, data))

        # fmt: off
        self.view.liabilities_tree_view.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.view.liabilities_tree_view.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.view.liabilities_tree_view.expandAll()
        # fmt: on
