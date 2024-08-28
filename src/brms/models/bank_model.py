from brms.models.bank_book_model import BankBankingBookModel, BankTradingBookModel
from brms.models.instruments import InstrumentFactory


class BankModel:

    def __init__(self) -> None:
        self.banking_book = BankBankingBookModel()
        self.trading_book = BankTradingBookModel()

    def add_cash(self, value: float) -> None:
        """
        Adds cash to the banking book.

        :param value: The amount of cash to add.
        :type value: float
        """

        self.banking_book.add_asset(InstrumentFactory.create_cash(value))

    def add_demand_deposits(self, value: float) -> None:
        """
        Adds demand deposits to the banking book.

        :param value: The value of the demand deposits to add.
        :type value: float
        """

        self.banking_book.add_liability(InstrumentFactory.create_demand_deposits(value))
