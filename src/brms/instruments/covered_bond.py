"""Define the CoveredBond class representing covered bond instruments."""

from brms.instruments.base import Instrument
from brms.instruments.valuation import ValuationVisitor
from brms.models.scenario import Scenario


class CoveredBond(Instrument):
    """A class to represent covered bond instruments."""

    def accept(self, visitor: ValuationVisitor, scenario: Scenario) -> float:
        """Accept a valuation visitor to calculate the instrument's value."""
        return visitor.value_covered_bond(self, scenario)
