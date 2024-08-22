from .bank_banking_book_model import BankBankingBookModel
from .bank_trading_book_model import BankTradingBookModel


class BankModel:

    def __init__(self) -> None:
        self.banking_book = BankBankingBookModel()
        self.trading_book = BankTradingBookModel()
