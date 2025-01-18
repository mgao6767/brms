"""Define the Cash class representing cash."""

from typing import TYPE_CHECKING

from brms.instruments.base import Instrument

if TYPE_CHECKING:
    from brms.instruments.visitors import Visitor


class Cash(Instrument):
    """A class to represent cash."""

    def __init__(self, value: float = 0.0) -> None:
        super().__init__(name="Cash")
        self.value = value

    def accept(self, visitor: "Visitor") -> None:
        """Accept a visitor."""
        visitor.visit_cash(self)
