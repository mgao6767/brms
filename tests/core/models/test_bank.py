"""Tests for the Bank model."""

# ruff: noqa: S101

from unittest.mock import MagicMock

from brms.core.models.bank import Bank
from brms.core.stores.instrument_store import InstrumentStore
from brms.core.stores.position_store import PositionStore


def test_bank_owns_books_and_ledger() -> None:
    """Bank stores name, instruments, positions, and the ledger."""
    instruments = InstrumentStore()
    positions = PositionStore()
    ledger = MagicMock()
    bank = Bank(name="Test Bank", instruments=instruments, positions=positions, ledger=ledger)
    assert bank.name == "Test Bank"
    assert bank.instruments is instruments
    assert bank.positions is positions
    assert bank.ledger is ledger
