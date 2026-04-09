"""Contain valuation visitor classes for banking and trading books."""

import datetime
from abc import abstractmethod
from functools import wraps
from typing import TYPE_CHECKING, Union

import QuantLib as ql  # noqa: N813

from brms.core.models.instruments.base import BookType, InstrumentClass
from brms.core.visitors.base import Visitor
from brms.core.services.yield_curve_service import YieldCurveService
from brms.core.utils import pydate_to_qldate

if TYPE_CHECKING:
    from brms.core.models.instruments.bonds import CoveredBond, FixedRateBond
    from brms.core.models.instruments.deposits import Cash, Deposit
    from brms.core.models.instruments.equity import CommonEquity
    from brms.core.models.instruments.loans import AmortizingFixedRateLoan, CreditCard, PersonalLoan
    from brms.core.models.market_data import MarketState


class ValuationVisitor(Visitor):
    """Abstract base class for valuation visitors."""

    def __init__(self, market_state: "MarketState", *, valuation_date: datetime.date | None = None) -> None:
        """Initialise the ValuationVisitor with a MarketState and an optional valuation date."""
        self.market_state = market_state
        self.valuation_date = valuation_date
        self.term_structure_handle = ql.RelinkableYieldTermStructureHandle()
        self.bond_engine = ql.DiscountingBondEngine(self.term_structure_handle)
        if self.valuation_date is not None:
            self.set_date(self.valuation_date)

    def _build_term_structure(self) -> ql.YieldTermStructure:
        """Build a QuantLib yield term structure from the current MarketState yields."""
        yields = self.market_state.yields
        maturity_labels = list(yields.index)
        rates = list(yields.values)
        return YieldCurveService.build_yield_curve(self.market_state.date, maturity_labels, rates)

    def set_date(self, date: datetime.date) -> None:
        """Set the valuation date and relink the term structure from the MarketState."""
        self.valuation_date = date
        term_structure = self._build_term_structure()
        self.term_structure_handle.linkTo(term_structure)

    def visit_cash(self, instrument: "Cash") -> None:
        """Value cash — no pricing required."""

    def visit_deposit(self, instrument: "Deposit") -> None:
        """Value deposit — no pricing required."""

    def visit_common_equity(self, instrument: "CommonEquity") -> None:
        """Value common equity — no pricing required."""

    @abstractmethod
    def visit_fixed_rate_bond(self, instrument: "FixedRateBond") -> None:
        """Value a fixed rate bond."""

    @abstractmethod
    def visit_amortizing_fixed_rate_loan(self, instrument: "AmortizingFixedRateLoan") -> None:
        """Value an amortizing fixed rate loan."""

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
            msg = "Valuation date must be set before valuation."
            raise ValueError(msg)
        instrument.set_pricing_engine(self.bond_engine)
        # Restore previous evaluation date afterwards to avoid side-effects
        old_evaluation_date = ql.Settings.instance().evaluationDate
        ql.Settings.instance().evaluationDate = pydate_to_qldate(self.valuation_date)
        npv = instrument.instrument.NPV()
        ql.Settings.instance().evaluationDate = old_evaluation_date
        return npv


class BankingBookValuationVisitor(ValuationVisitor):
    """A visitor for banking book valuation."""

    @staticmethod
    def banking_book_only(method):  # noqa: ANN001, ANN205
        """Skip instruments not in the banking book."""

        @wraps(method)
        def wrapper(self, instrument, *args, **kwargs):  # noqa: ANN001, ANN002, ANN003, ANN202
            if instrument.book_type != BookType.BANKING:
                return None
            return method(self, instrument, *args, **kwargs)

        return wrapper

    @banking_book_only
    def visit_fixed_rate_bond(self, instrument: "FixedRateBond") -> None:
        """Value a fixed rate bond."""
        assert self.valuation_date is not None  # noqa: S101
        match instrument.instrument_class:
            case InstrumentClass.HTM:
                instrument.value = instrument.notional(self.valuation_date)
            case InstrumentClass.FVOCI | InstrumentClass.FVTPL:
                instrument.value = self._value_fair_value_security(instrument)

    @banking_book_only
    def visit_amortizing_fixed_rate_loan(self, instrument: "AmortizingFixedRateLoan") -> None:
        """Value an amortizing fixed rate loan."""
        assert self.valuation_date is not None  # noqa: S101
        match instrument.instrument_class:
            case InstrumentClass.HTM | InstrumentClass.LOAN_AND_MORTGAGE:
                _, _, outstanding_balance = instrument.payment_schedule()
                if self.valuation_date < min(d for d, _ in outstanding_balance):
                    # No payments yet — the amount is the notional amount
                    instrument.value = instrument.notional(instrument.issue_date)
                else:
                    # At least some payments made — use the latest outstanding amount
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
    def trading_book_only(method):  # noqa: ANN001, ANN205
        """Skip instruments not in the trading book."""

        @wraps(method)
        def wrapper(self, instrument, *args, **kwargs):  # noqa: ANN001, ANN002, ANN003, ANN202
            if instrument.book_type != BookType.TRADING:
                return None
            return method(self, instrument, *args, **kwargs)

        return wrapper

    @trading_book_only
    def visit_fixed_rate_bond(self, instrument: "FixedRateBond") -> None:
        """Value a fixed rate bond."""
        instrument.value = self._value_fair_value_security(instrument)

    @trading_book_only
    def visit_amortizing_fixed_rate_loan(self, instrument: "AmortizingFixedRateLoan") -> None:
        """Value an amortizing fixed rate loan."""
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
