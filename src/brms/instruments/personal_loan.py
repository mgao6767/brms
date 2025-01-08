"""Define the PersonalLoan class representing personal loan instruments."""

from brms.instruments.base import Instrument
from brms.instruments.registry import RetailInstrumentRegistry
from brms.instruments.valuation import ValuationVisitor
from brms.models.scenario import Scenario


class PersonalLoan(Instrument):
    """A class to represent personal loan instruments."""

    def accept(self, visitor: ValuationVisitor, scenario: Scenario) -> float:
        """Accept a valuation visitor to calculate the instrument's value."""
        return visitor.value_personal_loan(self, scenario)


RetailInstrumentRegistry.register(PersonalLoan)
