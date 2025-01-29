"""Define the `Bank` class."""

import itertools
from typing import TYPE_CHECKING

from brms.accounting.account import AccountBalances, BankChartOfAccounts
from brms.accounting.ledger import Ledger
from brms.instruments.base import InstrumentClass
from brms.instruments.cash import Cash
from brms.instruments.mortgage import Mortgage
from brms.instruments.fixed_rate_bond import FixedRateBond
from brms.models.accountant import Accountant
from brms.models.bank_book import BankingBook, Position, TradingBook

if TYPE_CHECKING:
    from collections.abc import Generator

    from brms.instruments.base import Instrument
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

    def process_transaction(self, transaction: "Transaction") -> bool:
        """Ask the accountant to process the transaction."""
        return self.accountant.process_transaction(transaction)

    def undo_last_transaction(self) -> None:
        """Asks Accountant to reverse last transaction."""
        self.accountant.undo_last_transaction()

    def get_fair_value_instruments(self, position: Position) -> "Generator[Instrument, None, None]":
        """Get fair value instruments based on position."""
        match position:
            case Position.LONG:
                instruments = itertools.chain(self.banking_book.long_exposure, self.trading_book.long_exposure)
            case Position.SHORT:
                instruments = itertools.chain(self.banking_book.short_exposure, self.trading_book.short_exposure)

        for instrument in instruments:
            if instrument.instrument_class in (InstrumentClass.FVOCI, InstrumentClass.FVTPL):
                yield instrument

    def get_mortgage_instruments(self) -> "Generator[Mortgage, None, None]":
        """Get all mortgage instruments from the banking book (long-only)."""
        for instrument in self.banking_book.long_exposure:
            if isinstance(instrument, Mortgage):
                yield instrument

    def get_htm_bond_instruments(self) -> "Generator[FixedRateBond, None, None]":
        """Get all HTM bond instruments from the banking book (long-only)."""
        for instrument in self.banking_book.long_exposure:
            if isinstance(instrument, FixedRateBond) and instrument.instrument_class == InstrumentClass.HTM:
                yield instrument
