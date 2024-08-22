from brms.models.bank_trading_book_model import BankTradingBookModel
from brms.views.bank_trading_book_widget import BankTradingBookWidget


class TradingBookController:

    def __init__(self, model: BankTradingBookModel, view: BankTradingBookWidget):
        self.model = model
        self.view = view

    def add_asset(self):
        pass

    def remove_asset(self):
        pass

    def add_liability(self):
        pass

    def remove_liability(self):
        pass
