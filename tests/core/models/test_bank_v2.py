"""Tests for the Bank model V2."""

# ruff: noqa: S101

from unittest.mock import MagicMock

from brms.core.models.bank import Bank
from brms.core.stores.instrument_store import InstrumentStore
from brms.core.stores.position_store import PositionStore


def test_bank_has_stores_and_ledger() -> None:
    """Bank stores name, instruments, positions, and ledger."""
    instruments = InstrumentStore()
    positions = PositionStore()
    ledger = MagicMock()
    bank = Bank(name="Test", instruments=instruments, positions=positions, ledger=ledger)
    assert bank.name == "Test"
    assert isinstance(bank.instruments, InstrumentStore)
    assert isinstance(bank.positions, PositionStore)
    assert bank.ledger is ledger
