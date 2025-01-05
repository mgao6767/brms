"""Define the base classes and enumerations for financial instruments."""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional


class BookType(Enum):
    """Enumeration for different types of books.

    Before a bank can calculate RWA for credit risk and RWA for market risk, it must follow the requirements of RBC25 to
    identify the instruments that are in the trading book. The banking book comprises all instruments that are not in
    the trading book and all other assets of the bank.
    """

    BANKING_BOOK = "Banking Book"
    TRADING_BOOK = "Trading Book"


class BalanceSheetCategory(Enum):
    """Enumeration for the category of the balance sheet an instrument is on."""

    ASSET = "Asset"
    LIABILITY = "Liability"
    EQUITY = "Equity"


class Instrument(ABC):
    """Abstract base class for financial instruments."""

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
    def value(self, scenario: dict) -> float:
        """Calculate the instrument's value based on the given scenario."""


class CompositeInstrument(Instrument):
    """Composite class for financial instruments.

    This class allows for the aggregation of multiple financial instruments into a single composite instrument.
    It can be used to represent a collection of assets, liabilities, or equities for a bank.
    """

    def __init__(self) -> None:
        """Initialize a composite instrument with an empty list of instruments."""
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

    def value(self, scenario: dict) -> float:
        """Calculate the composite instrument's value based on the given scenario."""
        return sum(instrument.value(scenario) for instrument in self._instruments)
