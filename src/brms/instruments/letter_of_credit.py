"""Define the LetterOfCredit classes representing letters of credit."""

from brms.instruments.base import Instrument
from brms.instruments.registry import OffBalanceSheetInstrumentRegistry
from brms.instruments.valuation import ValuationVisitor
from brms.models.scenario import Scenario


class LetterOfCredit(Instrument):
    """A class to represent letter of credit instruments."""

    def accept(self, visitor: ValuationVisitor, scenario: Scenario) -> float:
        """Accept a valuation visitor to calculate the instrument's value."""
        raise NotImplementedError


class StandByLetterOfCredit(Instrument):
    """A class to represent standby letter of credit instruments."""

    def accept(self, visitor: ValuationVisitor, scenario: Scenario) -> float:
        """Accept a valuation visitor to calculate the instrument's value."""
        raise NotImplementedError


class TradeLetterOfCredit(Instrument):
    """A class to represent trade letter of credit instruments."""

    def accept(self, visitor: ValuationVisitor, scenario: Scenario) -> float:
        """Accept a valuation visitor to calculate the instrument's value."""
        raise NotImplementedError


OffBalanceSheetInstrumentRegistry.register(StandByLetterOfCredit)
OffBalanceSheetInstrumentRegistry.register(TradeLetterOfCredit)
