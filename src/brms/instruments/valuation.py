"""Contain valuation visitor classes for banking and trading books."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

import QuantLib as ql

from brms.models.base import ScenarioData
from brms.models.scenario import Scenario
from brms.utils import pydate_to_qldate

if TYPE_CHECKING:
    from brms.instruments.fixed_rate_bond import FixedRateBond


class ValuationVisitor(ABC):
    """Abstract base class for valuation visitors."""

    @abstractmethod
    def value_fixed_rate_bond(self, instrument: "FixedRateBond", scenario: Scenario) -> float:
        """Value a fixed rate bond given a scenario."""


class BankingBookValuationVisitor(ValuationVisitor):
    """A visitor for banking book valuation."""

    def value_fixed_rate_bond(self, instrument: "FixedRateBond", scenario: Scenario) -> float:
        """Value a fixed rate bond given a scenario."""
        valuation_date = scenario.date
        return instrument.notional(valuation_date)


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
