from collections import defaultdict

import QuantLib as ql

from .bank_book_model import BankBookModel


class BankTradingBookModel(BankBookModel):

    def __init__(self) -> None:
        super().__init__()

    def assets_data(self):

        grouped_assets = defaultdict(lambda: defaultdict(list))
        # Group assets by class type and name
        for asset in self.assets:
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

        return data
