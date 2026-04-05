"""Bank model holding InstrumentStore, PositionStore, and Ledger."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from brms.core.stores.instrument_store import InstrumentStore
    from brms.core.stores.position_store import PositionStore


class Bank:
    """Holds instruments, positions, and ledger. No business logic."""

    def __init__(self, name: str, instruments: InstrumentStore, positions: PositionStore, ledger: object) -> None:
        """Initialize a bank with its stores and ledger."""
        self.name = name
        self.instruments = instruments
        self.positions = positions
        self.ledger = ledger
