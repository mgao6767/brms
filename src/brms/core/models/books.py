"""Banking and trading book containers for financial instruments."""

from __future__ import annotations

from enum import Enum, auto
from typing import TYPE_CHECKING, ClassVar

from brms.core.exceptions import InstrumentNotFoundError
from brms.core.models.instruments.base import BookType, Instrument


class Position(Enum):
    """Enumeration for position types (LONG or SHORT)."""

    LONG = auto()
    SHORT = auto()

if TYPE_CHECKING:
    from collections.abc import Iterator


class BankingBook:
    """Holds instruments assigned to the banking book."""

    book_type: ClassVar[BookType] = BookType.BANKING

    def __init__(self) -> None:
        """Initialize an empty banking book."""
        self._instruments: list[Instrument] = []

    def add(self, instrument: Instrument) -> None:
        """Append an instrument to the book."""
        self._instruments.append(instrument)

    def remove(self, instrument_id: str) -> None:
        """Remove an instrument by id; raise InstrumentNotFoundError if absent."""
        for i, inst in enumerate(self._instruments):
            if inst.id == instrument_id:
                self._instruments.pop(i)
                return
        raise InstrumentNotFoundError(instrument_id)

    def __iter__(self) -> Iterator[Instrument]:
        """Iterate over instruments in the book."""
        return iter(self._instruments)

    def __len__(self) -> int:
        """Return the number of instruments in the book."""
        return len(self._instruments)


class TradingBook:
    """Holds instruments assigned to the trading book."""

    book_type: ClassVar[BookType] = BookType.TRADING

    def __init__(self) -> None:
        """Initialize an empty trading book."""
        self._instruments: list[Instrument] = []

    def add(self, instrument: Instrument) -> None:
        """Append an instrument to the book."""
        self._instruments.append(instrument)

    def remove(self, instrument_id: str) -> None:
        """Remove an instrument by id; raise InstrumentNotFoundError if absent."""
        for i, inst in enumerate(self._instruments):
            if inst.id == instrument_id:
                self._instruments.pop(i)
                return
        raise InstrumentNotFoundError(instrument_id)

    def __iter__(self) -> Iterator[Instrument]:
        """Iterate over instruments in the book."""
        return iter(self._instruments)

    def __len__(self) -> int:
        """Return the number of instruments in the book."""
        return len(self._instruments)
