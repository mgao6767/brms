"""Deposit instrument classes for the core domain model."""

from __future__ import annotations

from typing import TYPE_CHECKING

from brms.core.enums import InstrumentType
from brms.core.models.instruments.base import Instrument

if TYPE_CHECKING:
    from brms.core.visitors.base import Visitor


class Cash(Instrument):
    """A class to represent cash."""

    def __init__(self) -> None:
        """Initialize cash."""
        super().__init__(name="Cash")
        self.instrument_type = InstrumentType.CASH

    def accept(self, visitor: Visitor) -> None:
        """Accept a visitor."""
        visitor.visit_cash(self)  # type: ignore[union-attr]


class Deposit(Instrument):
    """A class to represent customer deposit."""

    def __init__(self, *, name: str = "Deposit") -> None:
        """Initialize a deposit with an optional name.

        Args:
            name (str): The name of the deposit. Defaults to "Deposit".

        """
        super().__init__(name=name)
        self.instrument_type = InstrumentType.DEPOSIT

    def accept(self, visitor: Visitor) -> None:
        """Accept a visitor."""
        visitor.visit_deposit(self)  # type: ignore[union-attr]
