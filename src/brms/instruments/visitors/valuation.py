"""Contain valuation visitor classes for banking and trading books."""

from abc import abstractmethod
from functools import wraps
from typing import TYPE_CHECKING, Union

import QuantLib as ql  # noqa: N813

from brms.instruments.base import BookType
from brms.instruments.visitors import Visitor
from brms.models.base import InstrumentClass, ScenarioData
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
    from brms.models.scenario import Scenario


class ValuationVisitor(Visitor):
    """Abstract base class for valuation visitors."""

    def __init__(self, scenario: "Scenario") -> None:
        """Initialize the ValuationVisitor with a scenario."""
        self.scenario = scenario

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
        valuation_date = self.scenario.date

        term_structure = self.scenario.data[ScenarioMetric.YIELD_TERM_STRUCTURE]
        bond_engine = ql.DiscountingBondEngine(ql.YieldTermStructureHandle(term_structure))
        instrument.set_pricing_engine(bond_engine)
        # Just being cautious, restore previous evaluation date afterwards
        old_evaluation_date = ql.Settings.instance().evaluationDate
        ql.Settings.instance().evaluationDate = pydate_to_qldate(valuation_date)
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
        valuation_date = self.scenario.date
        match instrument.instrument_class:
            case InstrumentClass.HTM:
                instrument.value = instrument.notional(valuation_date)
            case InstrumentClass.FVOCI | InstrumentClass.FVTPL:
                instrument.value = self._value_fair_value_security(instrument)

    @banking_book_only
    def visit_amortizing_fixed_rate_loan(self, instrument: "AmortizingFixedRateLoan") -> None:
        """Value an amortizing fixed rate bond."""
        valuation_date = self.scenario.date
        instrument.value = instrument.notional(valuation_date)

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
