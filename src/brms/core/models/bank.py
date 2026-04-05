"""Bank model holding InstrumentStore, PositionStore, and Ledger."""

from __future__ import annotations

from typing import TYPE_CHECKING

from brms.core.enums import BookType

if TYPE_CHECKING:
    from brms.core.stores.instrument_store import InstrumentStore
    from brms.core.stores.position_store import PositionStore


class _BookView:
    """Lightweight view over a Bank's positions filtered by book type.

    Provides iteration over instruments for backward compatibility
    with BankBookController which expects an iterable of instruments.
    """

    def __init__(self, bank: Bank, book_type: BookType) -> None:
        self._bank = bank
        self.book_type = book_type

    def __iter__(self):  # noqa: ANN204
        """Iterate over instruments in this book's open positions."""
        for pos in self._bank.positions.by_book(self.book_type):
            try:
                yield self._bank.instruments.get(pos.instrument_id)
            except KeyError:
                continue

    def __len__(self) -> int:
        """Return count of open positions in this book."""
        return len(self._bank.positions.by_book(self.book_type))

    def get_instrument_by_id(self, instrument_id: str):  # noqa: ANN201
        """Look up instrument by id."""
        return self._bank.instruments.get(instrument_id)


class Bank:
    """Holds instruments, positions, and ledger. No business logic."""

    def __init__(self, name: str, instruments: InstrumentStore, positions: PositionStore, ledger: object) -> None:
        """Initialize a bank with its stores and ledger."""
        self.name = name
        self.instruments = instruments
        self.positions = positions
        self.ledger = ledger

    @property
    def banking_book(self) -> _BookView:
        """View of banking book positions (for backward compatibility)."""
        return _BookView(self, BookType.BANKING)

    @property
    def trading_book(self) -> _BookView:
        """View of trading book positions (for backward compatibility)."""
        return _BookView(self, BookType.TRADING)
