from brms.models.bank_book_model import BankBankingBookModel, BankTradingBookModel


class BankModel:

    def __init__(self) -> None:
        self.banking_book = BankBankingBookModel()
        self.trading_book = BankTradingBookModel()
