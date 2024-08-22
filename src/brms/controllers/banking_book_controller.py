from PySide6.QtWidgets import QHeaderView

from brms.models.bank_banking_book_model import BankBankingBookModel
from brms.views.bank_banking_book_widget import BankBankingBookWidget
from brms.views.base import TreeModel


class BankingBookController:

    def __init__(self, model: BankBankingBookModel, view: BankBankingBookWidget):
        self.model = model
        self.view = view

        self._test()

    def add_asset(self):
        pass

    def remove_asset(self):
        pass

    def add_liability(self):
        pass

    def remove_liability(self):
        pass

    def _test(self):
        # Testing
        headers = ["Asset", "Value"]
        data = [
            {"data": ["Cash", "3000"]},
            {
                "data": ["Loans", "10000"],
                "children": [
                    {"data": ["C&I loans", "5000"]},
                    {"data": ["Consumer loans", "3000"]},
                    {"data": ["Mortgages", "2000"]},
                ],
            },
        ]
        self.view.assets_tree_view.setModel(TreeModel(headers, data))

        headers = ["Liability & Equity", "Value"]
        data = [
            {
                "data": ["Deposits", "10000"],
                "children": [{"data": ["Demand deposits", "5000"]}],
                "children": [{"data": ["Term deposits", "5000"]}],
            },
            {
                "data": ["Certificate of Deposits", "2000"],
            },
            {"data": ["Long-term debt", "500"]},
            {"data": ["Equity", "500"]},
        ]
        self.view.liabilities_tree_view.setModel(TreeModel(headers, data))

        # fmt: off
        self.view.assets_tree_view.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.view.assets_tree_view.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.view.liabilities_tree_view.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.view.liabilities_tree_view.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)

        self.view.assets_tree_view.expandAll()
        self.view.liabilities_tree_view.expandAll()
        # fmt: on
