"""Define the CreditCard class representing credit card instruments."""

from brms.instruments.base import Instrument
from brms.instruments.valuation import ValuationVisitor
from brms.models.scenario import Scenario


class CreditCard(Instrument):
    """A class to represent credit card instruments."""

    def accept(self, visitor: ValuationVisitor, scenario: Scenario) -> float:
        """Accept a valuation visitor to calculate the instrument's value."""
        return visitor.value_credit_card(self, scenario)
