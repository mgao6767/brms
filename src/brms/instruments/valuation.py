"""Contain valuation visitor classes for banking and trading books."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from brms.models.scenario import Scenario

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
        raise NotImplementedError
