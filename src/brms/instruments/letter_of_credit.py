"""Define the LetterOfCredit classes representing letters of credit."""

from typing import TYPE_CHECKING

from brms.instruments.base import Instrument
from brms.instruments.registry import OffBalanceSheetInstrumentRegistry

if TYPE_CHECKING:
    from brms.instruments.visitor import Visitor


class LetterOfCredit(Instrument):
    """A class to represent letter of credit instruments."""

    def accept(self, visitor: "Visitor") -> float:
        """Accept a visitor."""
        raise NotImplementedError


class StandByLetterOfCredit(Instrument):
    """A class to represent standby letter of credit instruments."""

    def accept(self, visitor: "Visitor") -> float:
        """Accept a visitor."""
        raise NotImplementedError


class TradeLetterOfCredit(Instrument):
    """A class to represent trade letter of credit instruments."""

    def accept(self, visitor: "Visitor") -> float:
        """Accept a visitor."""
        raise NotImplementedError


OffBalanceSheetInstrumentRegistry.register(StandByLetterOfCredit)
OffBalanceSheetInstrumentRegistry.register(TradeLetterOfCredit)
