"""Define the PersonalLoan class representing personal loan instruments."""

from typing import TYPE_CHECKING

from brms.instruments.base import Instrument
from brms.instruments.registry import RetailInstrumentRegistry

if TYPE_CHECKING:
    from brms.instruments.visitor import Visitor


class PersonalLoan(Instrument):
    """A class to represent personal loan instruments."""

    def accept(self, visitor: "Visitor") -> float:
        """Accept a visitor."""
        return visitor.visit_personal_loan(self)


RetailInstrumentRegistry.register(PersonalLoan)
