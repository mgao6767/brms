"""Define the `Bank` class."""

from typing import TYPE_CHECKING

from brms.accounting.account import AccountBalances, BankChartOfAccounts
from brms.accounting.ledger import Ledger
from brms.instruments.cash import Cash
from brms.models.accountant import Accountant
from brms.models.bank_book import BankingBook, Position, TradingBook

if TYPE_CHECKING:
    from brms.models.transaction import Transaction


class Bank:
    """Class representing a bank."""

    def __init__(self) -> None:
        """Initialize the Bank."""
        self.banking_book = BankingBook()
        self.trading_book = TradingBook()
        self.chart_of_accounts = BankChartOfAccounts()
        self.ledger = Ledger(self.chart_of_accounts)
        self.accountant = Accountant(self, self.ledger)

    def initialize(self, account_balances: AccountBalances | None = None) -> None:
        """Initialize the bank with a chart of accounts and account balances.

        This method only initializes the leger but not the bank's banking and trading books with instruments.

        # FIXME: instruments should not be initialized... account balance is just an accounting snapshot
        """
        if account_balances is None:
            account_balances = AccountBalances()
        self.ledger.set_account_balances(account_balances)
        # After initiating the leger, init the bank's banking and trading books with instruments
        cash = Cash(value=account_balances[self.chart_of_accounts.cash_account])
        self.banking_book.add_instrument(cash, Position.LONG)

    def initialize_from_transactions(self, transactions: list["Transaction"] | None = None) -> None:
        """Initialize the bank with a set of transactions.

        This method initializes both the bank's ledger and books with instruments.

        Importantly, the ledger is closed so we start from a fresh financial period.
        """
        transactions = transactions if transactions else []
        for transaction in transactions:
            self.process_transaction(transaction)
        # Close the ledger so we start from a fresh financial period
        # self.ledger.close_ledger(date=None)

    def process_transaction(self, transaction: "Transaction") -> bool:
        """Ask the accountant to process the transaction."""
        return self.accountant.process_transaction(transaction)

    def undo_last_transaction(self) -> None:
        """Asks Accountant to reverse last transaction."""
        self.accountant.undo_last_transaction()
