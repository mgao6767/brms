"""Define the base classes and enumerations for financial instruments."""

from abc import ABC, abstractmethod
from typing import Optional

from .valuation import ValuationVisitor


class Instrument(ABC):
    """Base class for financial instruments."""

    def __init__(self, name: str, parent: Optional["Instrument"] = None) -> None:
        """Initialize a financial instrument."""
        self.name = name
        self._parent = parent

    @property
    def parent(self) -> Optional["Instrument"]:
        """Get the parent instrument."""
        return self._parent

    @parent.setter
    def parent(self, parent: "Instrument") -> None:
        self._parent = parent

    def is_composite(self) -> bool:
        """Check if the instrument is composite."""
        return False

    @abstractmethod
    def accept(self, visitor: ValuationVisitor, scenario: dict) -> float:
        """Accept a valuation visitor to calculate the instrument's value."""


class CompositeInstrument(Instrument):
    """Composite class for financial instruments.

    This class allows for the aggregation of multiple financial instruments into a single composite instrument.
    It can be used to represent a collection of assets, liabilities, or equities for a bank.
    """

    def __init__(self, name: str, parent: Instrument | None = None) -> None:
        """Initialize a composite instrument with an empty list of instruments."""
        super().__init__(name, parent)
        self._instruments: list[Instrument] = []

    def add(self, instrument: Instrument) -> None:
        """Add an instrument to the composite."""
        self._instruments.append(instrument)

    def remove(self, instrument: Instrument) -> None:
        """Remove an instrument from the composite."""
        self._instruments.remove(instrument)

    def is_composite(self) -> bool:
        """Check if the instrument is composite."""
        return True

    def accept(self, visitor: ValuationVisitor, scenario: dict) -> float:
        """Accept a valuation visitor to calculate the composite instrument's value."""
        return sum(instrument.accept(visitor, scenario) for instrument in self._instruments)
