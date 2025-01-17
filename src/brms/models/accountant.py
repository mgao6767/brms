from typing import TYPE_CHECKING

from brms.accounting.journal import SimpleEntry
from brms.models.base import BookType
from brms.models.transaction import TransactionType

if TYPE_CHECKING:
    from brms.accounting.ledger import Ledger
    from brms.models.bank import Bank
    from brms.models.transaction import Transaction


class Accountant:
    """Accountant class responsible for managing bank and ledger."""

    def __init__(self, bank: "Bank", ledger: "Ledger") -> None:
        """Initialize an accountant."""
        self.bank = bank
        self.ledger = ledger

    def process_transaction(self, transaction: "Transaction") -> None:
        """Process a transaction based on its type."""
        match transaction.transaction_type:
            case TransactionType.BUY_INSTRUMENT:
                self._process_buy_instrument(transaction)
            case TransactionType.SELL_INSTRUMENT:
                self._process_sell_instrument(transaction)
            case TransactionType.INTEREST_PAYMENT:
                self._process_interest_payment(transaction)
            case TransactionType.INTEREST_RECEIPT:
                self._process_interest_receipt(transaction)
            case TransactionType.DIVIDEND_PAYMENT:
                self._process_dividend_payment(transaction)
            case TransactionType.DIVIDEND_RECEIPT:
                self._process_dividend_receipt(transaction)
            case TransactionType.FEE_PAYMENT:
                self._process_fee_payment(transaction)
            case TransactionType.FEE_RECEIPT:
                self._process_fee_receipt(transaction)

    def _process_buy_instrument(self, transaction: "Transaction") -> None:
        instrument = transaction.instrument
        # Add instrument to banking book
        if instrument.book_type == BookType.BANKING_BOOK:
            self.bank.banking_book.add_instrument(instrument, long_position=True)
        elif instrument.book_type == BookType.TRADING_BOOK:
            self.bank.trading_book.add_instrument(instrument, long_position=True)
        # Adjust cash
        # TODO: maybe should not directly modify cash value
        self.bank.banking_book.cash.value -= transaction.value
        # Accounting
        self.ledger.post(
            SimpleEntry(
                debit_account=transaction.account,
                credit_account=self.ledger.cash_account,
                value=transaction.value,
                date=transaction.date,
                description=transaction.description,
            ),
        )

    def _process_sell_instrument(self, transaction: "Transaction") -> None:
        instrument = transaction.instrument
        # Remove instrument from banking book
        if instrument.book_type == BookType.BANKING_BOOK:
            self.bank.banking_book.remove_instrument(instrument)
        elif instrument.book_type == BookType.TRADING_BOOK:
            self.bank.trading_book.remove_instrument(instrument)
        # Adjust cash
        # TODO: maybe should not directly modify cash value
        self.bank.banking_book.cash.value += instrument.value
        # Accounting
        # FIXME: selling instruments' accounting is composite, cash/income

    def _process_interest_payment(self, transaction: "Transaction") -> None:
        raise NotImplementedError

    def _process_interest_receipt(self, transaction: "Transaction") -> None:
        raise NotImplementedError

    def _process_dividend_payment(self, transaction: "Transaction") -> None:
        raise NotImplementedError

    def _process_dividend_receipt(self, transaction: "Transaction") -> None:
        raise NotImplementedError

    def _process_fee_payment(self, transaction: "Transaction") -> None:
        raise NotImplementedError

    def _process_fee_receipt(self, transaction: "Transaction") -> None:
        raise NotImplementedError
