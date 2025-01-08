"""Define the Commitment class representing commitments."""

from brms.instruments.base import Instrument
from brms.instruments.registry import OffBalanceSheetInstrumentRegistry
from brms.instruments.valuation import ValuationVisitor
from brms.models.scenario import Scenario


class Commitment(Instrument):
    """A class to represent commitments."""

    def accept(self, visitor: ValuationVisitor, scenario: Scenario) -> float:
        """Accept a valuation visitor to calculate the instrument's value."""
        raise NotImplementedError


OffBalanceSheetInstrumentRegistry.register(Commitment)
