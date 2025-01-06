"""Define the CommonEquity class representing common equity instruments."""

from brms.instruments.base import Instrument
from brms.instruments.valuation import ValuationVisitor
from brms.models.scenario import Scenario


class CommonEquity(Instrument):
    """A class to represent common equity instruments."""

    def __init__(self, name: str, parent: Instrument | None = None) -> None:
        """Initialize a CommonEquity instance."""
        super().__init__(name, parent)

    def accept(self, visitor: ValuationVisitor, scenario: Scenario) -> float:
        """Accept a valuation visitor to calculate the instrument's value."""
        return visitor.value_common_equity(self, scenario)
