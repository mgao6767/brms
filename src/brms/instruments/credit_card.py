"""Define the CreditCard class representing credit card instruments."""

from typing import TYPE_CHECKING

from brms.instruments.base import Instrument
from brms.instruments.registry import RetailInstrumentRegistry

if TYPE_CHECKING:
    from brms.instruments.visitor import Visitor


class CreditCard(Instrument):
    """A class to represent credit card instruments."""

    def accept(self, visitor: "Visitor") -> float:
        """Accept a visitor."""
        return visitor.visit_credit_card(self)


RetailInstrumentRegistry.register(CreditCard)
