"""
The base class for Banking Book and Trading Book
"""

from PySide6.QtCore import QObject, Signal

from brms.models.instruments import Cash, Instrument


class BankBookModel(QObject):

    asset_added = Signal()
    liability_added = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.assets = []
        self.liabilities = []

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
