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

    def __init__(self, *, name: str = "Deposit", interest_rate: float | None = None) -> None:
        """Initialize a deposit with an optional name and interest rate.

        Args:
            name: The name of the deposit. Defaults to "Deposit".
            interest_rate: Annual interest rate (e.g. 0.02 for 2%).
                When set, the deposit interest rules use this rate instead
                of their default.  Use 0.0 for a non-interest-bearing deposit.

        """
        super().__init__(name=name)
        self.instrument_type = InstrumentType.DEPOSIT
        self.interest_rate = interest_rate

    def accept(self, visitor: Visitor) -> None:
        """Accept a visitor."""
        visitor.visit_deposit(self)  # type: ignore[union-attr]
