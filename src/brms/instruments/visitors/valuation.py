"""Contain valuation visitor classes for banking and trading books."""

import datetime
from abc import abstractmethod
from functools import wraps
from typing import TYPE_CHECKING, Union

import QuantLib as ql  # noqa: N813

from brms.instruments.base import BookType
from brms.instruments.visitors import Visitor
from brms.models.base import InstrumentClass
from brms.models.scenario import ScenarioMetric
from brms.utils import pydate_to_qldate

if TYPE_CHECKING:
    from brms.instruments.amortizing_fixed_rate_loan import AmortizingFixedRateLoan
    from brms.instruments.cash import Cash
    from brms.instruments.common_equity import CommonEquity
    from brms.instruments.covered_bond import CoveredBond
    from brms.instruments.credit_card import CreditCard
    from brms.instruments.deposit import Deposit
    from brms.instruments.fixed_rate_bond import FixedRateBond
    from brms.instruments.personal_loan import PersonalLoan
    from brms.models.scenario import ScenarioManager


class ValuationVisitor(Visitor):
    """Abstract base class for valuation visitors."""

    def __init__(self, scenario_manager: "ScenarioManager", *, valuation_date: datetime.date | None = None) -> None:
        """Initialize the ValuationVisitor with a scenario manager and an optional valuation date."""
        self.valuation_date = valuation_date
        self.scenario_manager = scenario_manager
        self.term_structure_handle = ql.RelinkableYieldTermStructureHandle()
        self.bond_engine = ql.DiscountingBondEngine(self.term_structure_handle)
        if self.valuation_date is not None:
            self.set_date(self.valuation_date)

    def set_date(self, date: datetime.date, *, date_must_be_in_simulation: bool = True) -> None:
        """Set the date for the valuation and update the term structure."""
        # Relink term structure so that the bond pricing engine can automatically update all bonds
        self.valuation_date = date
        if date_must_be_in_simulation:
            scenario = self.scenario_manager.get_scenario(date)
            term_structure = scenario.data.get(ScenarioMetric.YIELD_TERM_STRUCTURE)
            self.term_structure_handle.linkTo(term_structure)

    def visit_cash(self, instrument: "Cash") -> None:
        """Value cash."""

    def visit_deposit(self, instrument: "Deposit") -> None:
        """Visit deposit."""

    def visit_common_equity(self, instrument: "CommonEquity") -> None:
        """Value common equity."""

    @abstractmethod
    def visit_fixed_rate_bond(self, instrument: "FixedRateBond") -> None:
        """Value a fixed rate bond."""

    @abstractmethod
    def visit_amortizing_fixed_rate_loan(self, instrument: "AmortizingFixedRateLoan") -> None:
        """Value an amortizing fixed rate bond."""

    @abstractmethod
    def visit_covered_bond(self, instrument: "CoveredBond") -> None:
        """Value a covered bond."""

    @abstractmethod
    def visit_personal_loan(self, instrument: "PersonalLoan") -> None:
        """Value a personal loan."""

    @abstractmethod
    def visit_credit_card(self, instrument: "CreditCard") -> None:
        """Value a credit card."""

    def _value_fair_value_security(self, instrument: Union["FixedRateBond", "AmortizingFixedRateLoan"]) -> float:
        if self.valuation_date is None:
            raise ValueError("Valuation date must be set before valuation.")
        instrument.set_pricing_engine(self.bond_engine)
        # Just being cautious, restore previous evaluation date afterwards
        old_evaluation_date = ql.Settings.instance().evaluationDate
        ql.Settings.instance().evaluationDate = pydate_to_qldate(self.valuation_date)
        npv = instrument.instrument.NPV()
        ql.Settings.instance().evaluationDate = old_evaluation_date
        return npv


class BankingBookValuationVisitor(ValuationVisitor):
    """A visitor for banking book valuation."""

    @staticmethod
    def banking_book_only(method):
        @wraps(method)
        def wrapper(self, instrument, *args, **kwargs):
            if instrument.book_type != BookType.BANKING_BOOK:
                return
            return method(self, instrument, *args, **kwargs)

        return wrapper

    @banking_book_only
    def visit_fixed_rate_bond(self, instrument: "FixedRateBond") -> None:
        """Value a fixed rate bond."""
        assert self.valuation_date is not None
        match instrument.instrument_class:
            case InstrumentClass.HTM:
                instrument.value = instrument.notional(self.valuation_date)
            case InstrumentClass.FVOCI | InstrumentClass.FVTPL:
                instrument.value = self._value_fair_value_security(instrument)

    @banking_book_only
    def visit_amortizing_fixed_rate_loan(self, instrument: "AmortizingFixedRateLoan") -> None:
        """Value an amortizing fixed rate bond."""
        assert self.valuation_date is not None
        match instrument.instrument_class:
            case InstrumentClass.HTM | InstrumentClass.LOAN_AND_MORTGAGE:
                _, _, outstanding_balance = instrument.payment_schedule()
                if self.valuation_date < min(d for d, _ in outstanding_balance):
                    # No payments yet, the amount is the notional amount
                    instrument.value = instrument.notional(instrument.issue_date)
                else:
                    # At least some payments made, the latest outstanding amount
                    last_outstanding = next(amt for d, amt in reversed(outstanding_balance) if d <= self.valuation_date)
                    instrument.value = last_outstanding
            case InstrumentClass.FVOCI | InstrumentClass.FVTPL:
                instrument.value = self._value_fair_value_security(instrument)

    @banking_book_only
    def visit_covered_bond(self, instrument: "CoveredBond") -> None:
        """Value a covered bond."""
        raise NotImplementedError

    @banking_book_only
    def visit_personal_loan(self, instrument: "PersonalLoan") -> None:
        """Value a personal loan."""
        raise NotImplementedError

    @banking_book_only
    def visit_credit_card(self, instrument: "CreditCard") -> None:
        """Value a credit card."""
        raise NotImplementedError


class TradingBookValuationVisitor(ValuationVisitor):
    """A visitor for trading book valuation."""

    @staticmethod
    def trading_book_only(method):
        @wraps(method)
        def wrapper(self, instrument, *args, **kwargs):
            if instrument.book_type != BookType.TRADING_BOOK:
                return
            return method(self, instrument, *args, **kwargs)

        return wrapper

    @trading_book_only
    def visit_fixed_rate_bond(self, instrument: "FixedRateBond") -> None:
        """Value a fixed rate bond."""
        instrument.value = self._value_fair_value_security(instrument)

    @trading_book_only
    def visit_amortizing_fixed_rate_loan(self, instrument: "AmortizingFixedRateLoan") -> None:
        """Value an amortizing fixed rate bond."""
        instrument.value = self._value_fair_value_security(instrument)

    @trading_book_only
    def visit_covered_bond(self, instrument: "CoveredBond") -> None:
        """Value a covered bond."""
        raise NotImplementedError

    @trading_book_only
    def visit_personal_loan(self, instrument: "PersonalLoan") -> None:
        """Value a personal loan."""
        raise NotImplementedError

    @trading_book_only
    def visit_credit_card(self, instrument: "CreditCard") -> None:
        """Value a credit card."""
        raise NotImplementedError
