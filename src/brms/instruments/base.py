"""Define the base classes and enumerations for financial instruments."""

from abc import ABC, abstractmethod
from collections.abc import Iterator
from typing import Optional

from brms.instruments.valuation import BankingBookValuationVisitor, TradingBookValuationVisitor, ValuationVisitor
from brms.models.base import BookType
from brms.models.scenario import Scenario


class Instrument(ABC):
    """Base class for financial instruments."""

    def __init__(self, name: str, parent: Optional["Instrument"] = None) -> None:
        """Initialize a financial instrument."""
        self.name = name
        self._parent = parent
        self._value: float = 0.0

    @property
    def parent(self) -> Optional["Instrument"]:
        """Get the parent instrument."""
        return self._parent

    @parent.setter
    def parent(self, parent: "Instrument") -> None:
        self._parent = parent

    @property
    def book_type(self) -> Optional["BookType"]:
        """Get the book type of the instrument."""
        return self._book_type

    @book_type.setter
    def book_type(self, book_type: "BookType") -> None:
        self._book_type = book_type

    @property
    def value(self) -> float:
        """Get the instrument's value."""
        return self._value

    @value.setter
    def value(self, value: float) -> None:
        self._value = value

    def is_composite(self) -> bool:
        """Check if the instrument is composite."""
        return False

    @abstractmethod
    def accept(self, visitor: ValuationVisitor, scenario: Scenario) -> float:
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

    def accept(self, visitor: ValuationVisitor, scenario: Scenario) -> float:
        """Accept a valuation visitor to calculate the composite instrument's value."""
        if isinstance(visitor, BankingBookValuationVisitor):
            return sum(
                instrument.accept(visitor, scenario)
                for instrument in self._instruments
                if instrument.book_type == BookType.BANKING_BOOK
            )
        if isinstance(visitor, TradingBookValuationVisitor):
            return sum(
                instrument.accept(visitor, scenario)
                for instrument in self._instruments
                if instrument.book_type == BookType.TRADING_BOOK
            )
        return 0.0

    def __iter__(self) -> Iterator[Instrument]:
        """Return an iterator over the instruments in the composite."""
        return iter(self._instruments)
