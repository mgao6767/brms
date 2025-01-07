"""Contain valuation visitor classes for banking and trading books."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

import QuantLib as ql

from brms.models.base import ScenarioData
from brms.models.scenario import Scenario
from brms.utils import pydate_to_qldate

if TYPE_CHECKING:
    from brms.instruments.common_equity import CommonEquity
    from brms.instruments.covered_bond import CoveredBond
    from brms.instruments.credit_card import CreditCard
    from brms.instruments.fixed_rate_bond import FixedRateBond
    from brms.instruments.personal_loan import PersonalLoan


class ValuationVisitor(ABC):
    """Abstract base class for valuation visitors."""

    def value_common_equity(self, instrument: "CommonEquity", scenario: Scenario) -> float:
        """Value common equity given a scenario."""
        return instrument.value

    @abstractmethod
    def value_fixed_rate_bond(self, instrument: "FixedRateBond", scenario: Scenario) -> float:
        """Value a fixed rate bond given a scenario."""

    @abstractmethod
    def value_covered_bond(self, instrument: "CoveredBond", scenario: Scenario) -> float:
        """Value a covered bond given a scenario."""

    @abstractmethod
    def value_personal_loan(self, instrument: "PersonalLoan", scenario: Scenario) -> float:
        """Value a personal loan given a scenario."""

    @abstractmethod
    def value_credit_card(self, instrument: "CreditCard", scenario: Scenario) -> float:
        """Value a credit card given a scenario."""


class BankingBookValuationVisitor(ValuationVisitor):
    """A visitor for banking book valuation."""

    def value_fixed_rate_bond(self, instrument: "FixedRateBond", scenario: Scenario) -> float:
        """Value a fixed rate bond given a scenario."""
        valuation_date = scenario.date
        return instrument.notional(valuation_date)

    def value_covered_bond(self, instrument: "CoveredBond", scenario: Scenario) -> float:
        """Value a covered bond given a scenario."""
        raise NotImplementedError

    def value_personal_loan(self, instrument: "PersonalLoan", scenario: Scenario) -> float:
        """Value a personal loan given a scenario."""
        raise NotImplementedError

    def value_credit_card(self, instrument: "CreditCard", scenario: Scenario) -> float:
        """Value a credit card given a scenario."""
        raise NotImplementedError


class TradingBookValuationVisitor(ValuationVisitor):
    """A visitor for trading book valuation."""

    def value_fixed_rate_bond(self, instrument: "FixedRateBond", scenario: Scenario) -> float:
        """Value a fixed rate bond given a scenario."""
        valuation_date = scenario.date

        term_structure: ql.YieldTermStructureHandle = scenario.data[ScenarioData.YIELD_TERM_STRUCTURE]
        bond_engine = ql.DiscountingBondEngine(term_structure)
        instrument.set_pricing_engine(bond_engine)

        # Just being cautious, restore previous evaluation date afterwards
        old_evaluation_date = ql.Settings.instance().evaluationDate
        ql.Settings.instance().evaluationDate = pydate_to_qldate(valuation_date)
        npv = instrument.instrument.NPV()
        ql.Settings.instance().evaluationDate = old_evaluation_date

        return npv

    def value_covered_bond(self, instrument: "CoveredBond", scenario: Scenario) -> float:
        """Value a covered bond given a scenario."""
        raise NotImplementedError

    def value_personal_loan(self, instrument: "PersonalLoan", scenario: Scenario) -> float:
        """Value a personal loan given a scenario."""
        raise NotImplementedError

    def value_credit_card(self, instrument: "CreditCard", scenario: Scenario) -> float:
        """Value a credit card given a scenario."""
        raise NotImplementedError
