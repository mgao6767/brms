import datetime

from brms.instruments.base import InstrumentClass
from brms.instruments.visitors.valuation import (
    BankingBookValuationVisitor,
    TradingBookValuationVisitor,
    ValuationVisitor,
)
from brms.models.bank import Bank
from brms.models.bank_book import Position
from brms.models.base import BookType
from brms.models.scenario import ScenarioManager
from brms.models.transaction import Transaction, TransactionFactory, TransactionType


class BankEngine:
    def __init__(self, bank: Bank, scenario_manager: ScenarioManager) -> None:
        self.bank = bank
        self.scenario_manager = scenario_manager
        self.banking_book_visitor = BankingBookValuationVisitor(self.scenario_manager)
        self.trading_book_visitor = TradingBookValuationVisitor(self.scenario_manager)

    def generate_transactions(self, date: datetime.date) -> list[Transaction]:
        """Generate all transactions for a given date."""
        transactions = []
        transactions.extend(self._generate_loan_repayments(date))
        transactions.extend(self._generate_coupon_payments(date))
        transactions.extend(self._generate_mark_to_market_adjustments(date))
        return transactions

    def _generate_loan_repayments(self, date: datetime.date) -> list[Transaction]:
        """Generate loan repayment transactions for loans due on this date."""
        return []

    def _generate_coupon_payments(self, date: datetime.date) -> list[Transaction]:
        """Generate coupon payment transactions for bonds with payments due on this date."""
        return []

    def _generate_mark_to_market_adjustments(self, date: datetime.date) -> list[Transaction]:
        """Generate mark-to-market adjustments for FVOCI and FVTPL instruments."""
        transactions = []
        visitor: ValuationVisitor
        for position in Position:
            for instrument in self.bank.get_fair_value_instruments(position):
                match instrument.book_type, position, instrument.instrument_class:
                    # Banking book FVOCI is long only
                    case (BookType.BANKING_BOOK, Position.LONG, InstrumentClass.FVOCI):
                        tx_type = TransactionType.SECURITY_FVOCI_MARK_TO_MARKET
                        visitor = self.banking_book_visitor
                    # Trading book FVTPL can be either long or short
                    case (BookType.TRADING_BOOK, Position.LONG, InstrumentClass.FVTPL):
                        tx_type = TransactionType.SECURITY_FVTPL_MARK_TO_MARKET
                        visitor = self.trading_book_visitor
                    case (BookType.TRADING_BOOK, Position.SHORT, InstrumentClass.FVTPL):
                        # TODO: this mark to market transaction may not be correct for short-side FVTPL
                        tx_type = TransactionType.SECURITY_FVTPL_MARK_TO_MARKET
                        visitor = self.trading_book_visitor
                    case _:
                        raise NotImplementedError
                tx = TransactionFactory.create_transaction(
                    bank=self.bank,
                    instrument=instrument,
                    transaction_type=tx_type,
                    transaction_date=date,
                    valuation_visitor=visitor,
                )
                transactions.append(tx)
        return transactions
