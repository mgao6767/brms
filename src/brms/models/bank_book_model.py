"""
The base class for Banking Book and Trading Book
"""

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
