"""
The base class for Banking Book and Trading Book
"""

class BankBookModel:

    def __init__(self) -> None:
        self.assets = []
        self.liabilities = []

    def add_asset(self, asset):
        self.assets.append(asset)

    def remove_asset(self, asset_id):
        self.assets = [asset for asset in self.assets if asset['id'] != asset_id]

    def add_liability(self, liability):
        self.liabilities.append(liability)

    def remove_liability(self, liability_id):
        self.liabilities = [liability for liability in self.liabilities if liability['id'] != liability_id]
