"""Define the `Bank` class."""

from typing import TYPE_CHECKING

from brms.accounting.account import AccountBalances, BankChartOfAccounts
from brms.accounting.ledger import Ledger
from brms.instruments.cash import Cash
from brms.instruments.visitors.valuation import BankingBookValuationVisitor, TradingBookValuationVisitor
from brms.models.accountant import Accountant
from brms.models.bank_book import BankingBook, Position, TradingBook

if TYPE_CHECKING:
    from brms.models.scenario import Scenario
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
        """Initialize the bank with a chart of accounts and account balances."""
        if account_balances is None:
            account_balances = AccountBalances()
        self.ledger.set_account_balances(account_balances)
        # After initiating the leger, init the bank's banking and trading books with instruments
        # TODO: init all instruments other than cash
        cash = Cash(value=account_balances[self.chart_of_accounts.cash_account])
        self.banking_book.add_instrument(cash, Position.LONG)

    def valuation(self, scenario: "Scenario") -> None:
        """Perform valuation on banking and trading book instruments."""
        self.banking_book.accept(BankingBookValuationVisitor(scenario))
        self.trading_book.accept(TradingBookValuationVisitor(scenario))

    def process_transaction(self, transaction: "Transaction") -> None:
        """Ask the accountant to process the transaction."""
        self.accountant.process_transaction(transaction)

    def undo_last_transaction(self) -> None:
        """Asks Accountant to reverse last transaction."""
        self.accountant.undo_last_transaction()
