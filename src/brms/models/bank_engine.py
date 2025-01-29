import datetime
from collections.abc import Generator

from brms.instruments.base import InstrumentClass
from brms.instruments.cash import Cash
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

    def generate_transactions(self, date: datetime.date) -> Generator[Transaction, None, None]:
        """Generate all transactions for a given date."""
        yield from self._generate_mortgage_repayments_due_to_maturity(date)
        yield from self._generate_mortgage_repayments(date)
        yield from self._generate_htm_bond_sale_due_to_maturity(date)
        yield from self._generate_htm_bond_coupon_payments(date)
        if self.scenario_manager.has_scenario(date):
            yield from self._generate_security_sales_due_to_maturity(date)
            yield from self._generate_mark_to_market_adjustments(date)

    def _generate_mortgage_repayments(self, date: datetime.date) -> Generator[Transaction, None, None]:
        """Generate mortgage repayment transactions for loans due on this date."""
        visitor = self.banking_book_visitor
        for mortgage in self.bank.get_mortgage_instruments():
            requirement = hasattr(mortgage, "maturity_date") and mortgage.maturity_date > date
            if not requirement:
                continue
            (interest_payments, principal_payments, _) = mortgage.payment_schedule()
            for (pmt_date, interest_pmt), (_, principal_pmt) in zip(interest_payments, principal_payments):
                # Given date may not coincide with a payment date
                if pmt_date == date:
                    # Interest payment
                    yield TransactionFactory.create_transaction(
                        bank=self.bank,
                        instrument=Cash(value=interest_pmt),
                        transaction_type=TransactionType.MORTGAGE_INTEREST_PAYMENT,
                        transaction_date=date,
                    )
                    # Principal payment (in case customers repay extra)
                    yield TransactionFactory.create_transaction(
                        bank=self.bank,
                        instrument=Cash(value=principal_pmt),
                        transaction_type=TransactionType.MORTGAGE_PRINCIPAL_PAYMENT,
                        transaction_date=date,
                        valuation_visitor=visitor,
                        # This is an extra kwarg specifically for this transaction
                        mortgage=mortgage,
                    )
                    break

    def _generate_mortgage_repayments_due_to_maturity(self, date: datetime.date) -> Generator[Transaction, None, None]:
        """Generate mortgage repayment transactions for loans maturing on this date."""
        for mortgage in self.bank.get_mortgage_instruments():
            requirement = hasattr(mortgage, "maturity_date") and mortgage.maturity_date <= date
            if not requirement:
                continue
            yield TransactionFactory.create_transaction(
                bank=self.bank,
                instrument=mortgage,
                transaction_type=TransactionType.LOAN_REPAYMENT,
                transaction_date=date,
            )

    def _generate_htm_bond_coupon_payments(self, date: datetime.date) -> Generator[Transaction, None, None]:
        """Generate coupon payment transactions for bonds with payments due on this date."""
        for bond in self.bank.get_htm_bond_instruments():
            requirement = hasattr(bond, "maturity_date") and bond.maturity_date > date
            if not requirement:
                continue
            cashflows = bond.payment_schedule()
            for pmt_date, coupon_pmt in cashflows:
                if pmt_date == date:
                    yield TransactionFactory.create_transaction(
                        bank=self.bank,
                        instrument=Cash(value=coupon_pmt),
                        transaction_type=TransactionType.SECURITY_INTEREST_EARNED,
                        transaction_date=date,
                    )
                    break

    def _generate_htm_bond_sale_due_to_maturity(self, date: datetime.date) -> Generator[Transaction, None, None]:
        for bond in self.bank.get_htm_bond_instruments():
            requirement = hasattr(bond, "maturity_date") and bond.maturity_date <= date
            if not requirement:
                continue
            yield TransactionFactory.create_transaction(
                bank=self.bank,
                instrument=bond,
                transaction_type=TransactionType.SECURITY_SALE_HTM,
                transaction_date=date,
            )

    def _generate_mark_to_market_adjustments(self, date: datetime.date) -> Generator[Transaction, None, None]:
        """Generate mark-to-market adjustments for FVOCI and FVTPL instruments."""
        visitor: ValuationVisitor
        for position in Position:
            for instrument in self.bank.get_fair_value_instruments(position):
                requirement = hasattr(instrument, "maturity_date") and instrument.maturity_date > date
                if not requirement:
                    continue
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
                yield TransactionFactory.create_transaction(
                    bank=self.bank,
                    instrument=instrument,
                    transaction_type=tx_type,
                    transaction_date=date,
                    valuation_visitor=visitor,
                )

    def _generate_security_sales_due_to_maturity(self, date: datetime.date) -> Generator[Transaction, None, None]:
        visitor: ValuationVisitor
        for position in Position:
            for instrument in self.bank.get_fair_value_instruments(position):
                requirement = hasattr(instrument, "maturity_date") and instrument.maturity_date <= date
                if not requirement:
                    continue
                match instrument.book_type, position, instrument.instrument_class:
                    # Banking book FVOCI is long only
                    case (BookType.BANKING_BOOK, Position.LONG, InstrumentClass.FVOCI):
                        tx_type = TransactionType.SECURITY_SALE_FVOCI
                        visitor = self.banking_book_visitor
                    # Trading book FVTPL can be either long or short
                    case (BookType.TRADING_BOOK, Position.LONG, InstrumentClass.FVTPL):
                        tx_type = TransactionType.SECURITY_SALE_TRADING
                        visitor = self.trading_book_visitor
                    case (BookType.TRADING_BOOK, Position.SHORT, InstrumentClass.FVTPL):
                        raise NotImplementedError
                    case _:
                        raise NotImplementedError
                yield TransactionFactory.create_transaction(
                    bank=self.bank,
                    instrument=instrument,
                    transaction_type=tx_type,
                    transaction_date=date,
                    valuation_visitor=visitor,
                )
