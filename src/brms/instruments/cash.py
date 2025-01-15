"""Define the Cash class representing cash."""

from typing import TYPE_CHECKING

from brms.instruments.base import Instrument

if TYPE_CHECKING:
    from brms.instruments.visitor import Visitor


class Cash(Instrument):
    """A class to represent cash."""

    def accept(self, visitor: "Visitor") -> float:
        """Accept a visitor."""
        return visitor.visit_cash(self)
