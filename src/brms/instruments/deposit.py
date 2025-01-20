"""Define the Deposit class representing customer deposit."""

from typing import TYPE_CHECKING

from brms.instruments.base import Instrument

if TYPE_CHECKING:
    from brms.instruments.visitors import Visitor


class Deposit(Instrument):
    """A class to represent customer deposit."""

    def __init__(self, *, name: str = "Deposit", value: float = 0.0) -> None:
        super().__init__(name=name)
        self.value = value

    def accept(self, visitor: "Visitor") -> None:
        """Accept a visitor."""
        visitor.visit_deposit(self)
