"""
The base class for Banking Book and Trading Book
"""

from collections import defaultdict

import QuantLib as ql
from PySide6.QtCore import QObject, Signal

from brms.models.instruments import Cash, Instrument


class BankBookModel(QObject):

    asset_added = Signal()
    liability_added = Signal()

    color_black = "black"
    color_green = "green"
    color_red = "red"

    def __init__(self) -> None:
        super().__init__()
        self.assets = []
        self.liabilities = []

        # Example structure of `self._assets_data`
        # This is used to store old data
        # [
        #     {"data": ["Cash", "3000", "color"]},
        #     {
        #         "data": ["Loans", "10000", "color"],
        #         "children": [
        #             {"data": ["C&I loans", "5000", "color"]},
        #             {"data": ["Consumer loans", "3000", "color"]},
        #             {"data": ["Mortgages", "2000", "color"]},
        #         ],
        #     },
        # ]
        self._assets_data = []
        self._liabilities_data = []

    def reset(self):
        self.assets.clear()
        self.liabilities.clear()
        self._assets_data.clear()
        self._liabilities_data.clear()

    def add_asset(self, asset: Instrument):
        if isinstance(asset, Cash):
            existing_cash = next((a for a in self.assets if isinstance(a, Cash)), None)
            if existing_cash:
                existing_cash.set_value(existing_cash.value() + asset.value())
            else:
                self.assets.append(asset)
            self.asset_added.emit()
            return

        self.assets.append(asset)
        self.asset_added.emit()

    def add_liability(self, liability):
        self.liabilities.append(liability)
        self.liability_added.emit()

    def _determine_color(self, current_value, old_value):
        if old_value is None:
            return self.color_black
        if current_value > old_value:
            return self.color_green
        if current_value < old_value:
            return self.color_red
        return self.color_black

    def _find_old_asset_data(self, asset_type):
        for _data in self._assets_data:
            if _data["data"][0] == asset_type:
                return _data
        return None

    def _find_old_liability_data(self, liability_type):
        for _data in self._liabilities_data:
            if _data["data"][0] == liability_type:
                return _data
        return None

    def _find_old_value(self, old_data, name):
        if old_data:
            for _data in old_data["children"]:
                if _data["data"][0] == name:
                    return _data["data"][1]
        return None


class BankBankingBookModel(BankBookModel):

    def __init__(self) -> None:
        super().__init__()

    def get_cash(self) -> float:
        existing_cash = next((a for a in self.assets if isinstance(a, Cash)), None)
        if existing_cash:
            return existing_cash.value()  # float value
        else:
            raise RuntimeError("No cash in the bank!")

    def set_cash(self, cash: float):
        assert isinstance(cash, float)
        existing_cash = next((a for a in self.assets if isinstance(a, Cash)), None)
        if existing_cash:
            existing_cash.set_value(cash)
        else:
            raise RuntimeError("No cash in the bank!")

    def assets_data(self):

        grouped_assets = defaultdict(lambda: defaultdict(list))
        # Group assets by class type and name
        # fmt: off
        for asset in self.assets:
            grouped_assets[type(asset).instrument_type][asset.name].append(asset)

        eval_date = ql.Settings.instance().evaluationDate

        # Create the data structure for the tree view
        data = []
        # Each asset_type is like Cash, Loans, etc
        for asset_type, assets_by_name in grouped_assets.items():
            old_data = self._find_old_asset_data(asset_type)
            asset_type_val = 0.0
            asset_type_data = {
                "data": [asset_type, asset_type_val, self.color_black],
                "children": [],
            }
            # Each asset within a type represents a specific asset
            for name, assets in assets_by_name.items():
                total_value = sum(a.value_on_banking_book(eval_date) for a in assets)
                asset_type_val += total_value
                old_asset_value = self._find_old_value(old_data, name)
                data_color = self._determine_color(total_value, old_asset_value)
                asset_type_data["children"].append({"data": [name, total_value, data_color]})

            old_asset_type_value = old_data["data"][1] if old_data else None
            data_color = self._determine_color(asset_type_val, old_asset_type_value)
            asset_type_data["data"] = [asset_type, asset_type_val, data_color]
            data.append(asset_type_data)

        self._assets_data = data
        return data

    def liabilities_data(self):

        grouped_liabilities = defaultdict(lambda: defaultdict(list))
        # Group liabilities by class type and name
        # fmt: off
        for liability in self.liabilities:
            grouped_liabilities[type(liability).instrument_type][liability.name].append(liability)

        eval_date = ql.Settings.instance().evaluationDate

        # Create the data structure for the tree view
        data = []
        # Each liability_type is like Loans, Mortgages, etc
        for liability_type, liabilities_by_name in grouped_liabilities.items():
            old_data = self._find_old_liability_data(liability_type)
            liability_type_val = 0.0
            liability_type_data = {
                "data": [liability_type, liability_type_val, self.color_black],
                "children": [],
            }
            # Each liability within a type represents a specific liability
            for name, liabilities in liabilities_by_name.items():
                total_value = sum(l.value_on_banking_book(eval_date) for l in liabilities)
                liability_type_val += total_value
                old_liability_value = self._find_old_value(old_data, name)
                data_color = self._determine_color(total_value, old_liability_value)
                liability_type_data["children"].append({"data": [name, total_value, data_color]})

            old_liability_type_value = old_data["data"][1] if old_data else None
            data_color = self._determine_color(liability_type_val, old_liability_type_value)
            liability_type_data["data"] = [liability_type, liability_type_val, data_color]
            data.append(liability_type_data)

        self._liabilities_data = data
        return data


class BankTradingBookModel(BankBookModel):

    def __init__(self) -> None:
        super().__init__()

    def assets_data(self):

        grouped_assets = defaultdict(lambda: defaultdict(list))
        # Group assets by class type and name
        # fmt: off
        for asset in self.assets:
            grouped_assets[type(asset).instrument_type][asset.name].append(asset)

        eval_date = ql.Settings.instance().evaluationDate

        # Create the data structure for the tree view
        data = []
        # Each asset_type is like Cash, Loans, etc
        for asset_type, assets_by_name in grouped_assets.items():
            old_data = self._find_old_asset_data(asset_type)
            asset_type_val = 0.0
            asset_type_data = {
                "data": [asset_type, asset_type_val, self.color_black],
                "children": [],
            }
            # Each asset within a type represents a specific asset
            for name, assets in assets_by_name.items():
                total_value = sum(a.value_on_trading_book(eval_date) for a in assets)
                asset_type_val += total_value
                old_asset_value = self._find_old_value(old_data, name)
                data_color = self._determine_color(total_value, old_asset_value)
                asset_type_data["children"].append({"data": [name, total_value, data_color]})

            old_asset_type_value = old_data["data"][1] if old_data else None
            data_color = self._determine_color(asset_type_val, old_asset_type_value)
            asset_type_data["data"] = [asset_type, asset_type_val, data_color]
            data.append(asset_type_data)

        self._assets_data = data
        return data

    def liabilities_data(self):

        grouped_liabilities = defaultdict(lambda: defaultdict(list))
        # Group liabilities by class type and name
        # fmt: off
        for liability in self.liabilities:
            grouped_liabilities[type(liability).instrument_type][liability.name].append(liability)

        eval_date = ql.Settings.instance().evaluationDate

        # Create the data structure for the tree view
        data = []
        # Each liability_type is like Loans, Mortgages, etc
        for liability_type, liabilities_by_name in grouped_liabilities.items():
            old_data = self._find_old_liability_data(liability_type)
            liability_type_val = 0.0
            liability_type_data = {
                "data": [liability_type, liability_type_val, self.color_black],
                "children": [],
            }
            # Each liability within a type represents a specific liability
            for name, liabilities in liabilities_by_name.items():
                total_value = sum(l.value_on_trading_book(eval_date) for l in liabilities)
                liability_type_val += total_value
                old_liability_value = self._find_old_value(old_data, name)
                data_color = self._determine_color(total_value, old_liability_value)
                liability_type_data["children"].append({"data": [name, total_value, data_color]})

            old_liability_type_value = old_data["data"][1] if old_data else None
            data_color = self._determine_color(liability_type_val, old_liability_type_value)
            liability_type_data["data"] = [liability_type, liability_type_val, data_color]
            data.append(liability_type_data)

        self._liabilities_data = data
        return data
