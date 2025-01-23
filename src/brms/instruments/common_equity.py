"""Define the CommonEquity class representing common equity instruments."""

from typing import TYPE_CHECKING

from brms.instruments.base import Instrument

if TYPE_CHECKING:
    from brms.instruments.visitors import Visitor


class CommonEquity(Instrument):
    """A class to represent common equity instruments."""

    def __init__(self, *, name: str = "Common Equity", value: float = 0.0) -> None:
        super().__init__(name=name)
        self.value = value

    def accept(self, visitor: "Visitor") -> None:
        """Accept a visitor."""
        visitor.visit_common_equity(self)
