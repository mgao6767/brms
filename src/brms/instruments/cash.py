"""Define the Cash class representing cash."""

from brms.instruments.base import Instrument
from brms.instruments.valuation import ValuationVisitor
from brms.models.scenario import Scenario


class Cash(Instrument):
    """A class to represent cash."""

    def accept(self, visitor: ValuationVisitor, scenario: Scenario) -> float:
        """Accept a valuation visitor to calculate the instrument's value."""
        return visitor.value_cash(self, scenario)
