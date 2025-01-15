"""Contain valuation visitor classes for banking and trading books."""

from abc import abstractmethod
from typing import TYPE_CHECKING

import QuantLib as ql  # noqa: N813

from brms.instruments.visitor import Visitor
from brms.models.base import ScenarioData
from brms.models.scenario import Scenario
from brms.utils import pydate_to_qldate

if TYPE_CHECKING:
    from brms.instruments.amortizing_fixed_rate_loan import AmortizingFixedRateLoan
    from brms.instruments.cash import Cash
    from brms.instruments.common_equity import CommonEquity
    from brms.instruments.covered_bond import CoveredBond
    from brms.instruments.credit_card import CreditCard
    from brms.instruments.fixed_rate_bond import FixedRateBond
    from brms.instruments.personal_loan import PersonalLoan
    from brms.models.scenario import Scenario


class ValuationVisitor(Visitor):
    """Abstract base class for valuation visitors."""

    def __init__(self, scenario: "Scenario") -> None:
        """Initialize the ValuationVisitor with a scenario."""
        self.scenario = scenario

    def visit_cash(self, instrument: "Cash") -> float:
        """Value cash."""
        return instrument.value

    def visit_common_equity(self, instrument: "CommonEquity") -> float:
        """Value common equity."""
        return instrument.value

    @abstractmethod
    def visit_fixed_rate_bond(self, instrument: "FixedRateBond") -> float:
        """Value a fixed rate bond."""

    @abstractmethod
    def visit_amortizing_fixed_rate_loan(self, instrument: "AmortizingFixedRateLoan") -> float:
        """Value an amortizing fixed rate bond."""

    @abstractmethod
    def visit_covered_bond(self, instrument: "CoveredBond") -> float:
        """Value a covered bond."""

    @abstractmethod
    def visit_personal_loan(self, instrument: "PersonalLoan") -> float:
        """Value a personal loan."""

    @abstractmethod
    def visit_credit_card(self, instrument: "CreditCard") -> float:
        """Value a credit card."""


class BankingBookValuationVisitor(ValuationVisitor):
    """A visitor for banking book valuation."""

    def visit_fixed_rate_bond(self, instrument: "FixedRateBond") -> float:
        """Value a fixed rate bond."""
        valuation_date = self.scenario.date
        return instrument.notional(valuation_date)

    def visit_amortizing_fixed_rate_loan(self, instrument: "AmortizingFixedRateLoan") -> float:
        """Value an amortizing fixed rate bond."""
        valuation_date = self.scenario.date
        return instrument.notional(valuation_date)

    def visit_covered_bond(self, instrument: "CoveredBond") -> float:
        """Value a covered bond."""
        raise NotImplementedError

    def visit_personal_loan(self, instrument: "PersonalLoan") -> float:
        """Value a personal loan."""
        raise NotImplementedError

    def visit_credit_card(self, instrument: "CreditCard") -> float:
        """Value a credit card."""
        raise NotImplementedError


class TradingBookValuationVisitor(ValuationVisitor):
    """A visitor for trading book valuation."""

    def visit_fixed_rate_bond(self, instrument: "FixedRateBond") -> float:
        """Value a fixed rate bond."""
        valuation_date = self.scenario.date

        term_structure: ql.YieldTermStructureHandle = self.scenario.data[ScenarioData.YIELD_TERM_STRUCTURE]
        bond_engine = ql.DiscountingBondEngine(term_structure)
        instrument.set_pricing_engine(bond_engine)

        # Just being cautious, restore previous evaluation date afterwards
        old_evaluation_date = ql.Settings.instance().evaluationDate
        ql.Settings.instance().evaluationDate = pydate_to_qldate(valuation_date)
        npv = instrument.instrument.NPV()
        ql.Settings.instance().evaluationDate = old_evaluation_date

        return npv

    def visit_amortizing_fixed_rate_loan(self, instrument: "AmortizingFixedRateLoan") -> float:
        """Value an amortizing fixed rate bond."""
        valuation_date = self.scenario.date

        term_structure: ql.YieldTermStructureHandle = self.scenario.data[ScenarioData.YIELD_TERM_STRUCTURE]
        bond_engine = ql.DiscountingBondEngine(term_structure)
        instrument.set_pricing_engine(bond_engine)

        # Just being cautious, restore previous evaluation date afterwards
        old_evaluation_date = ql.Settings.instance().evaluationDate
        ql.Settings.instance().evaluationDate = pydate_to_qldate(valuation_date)
        npv = instrument.instrument.NPV()
        ql.Settings.instance().evaluationDate = old_evaluation_date

        return npv

    def visit_covered_bond(self, instrument: "CoveredBond") -> float:
        """Value a covered bond."""
        raise NotImplementedError

    def visit_personal_loan(self, instrument: "PersonalLoan") -> float:
        """Value a personal loan."""
        raise NotImplementedError

    def visit_credit_card(self, instrument: "CreditCard") -> float:
        """Value a credit card."""
        raise NotImplementedError
