"""Tests for InstrumentStore."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from brms.core.enums import InstrumentType
from brms.core.stores.instrument_store import InstrumentStore


@pytest.fixture()
def store() -> InstrumentStore:
    return InstrumentStore()


def _make_instrument(instrument_id: str, instrument_type: InstrumentType) -> MagicMock:
    inst = MagicMock()
    inst.id = instrument_id
    inst.instrument_type = instrument_type
    return inst


def test_add_and_get(store: InstrumentStore) -> None:
    inst = _make_instrument("bond-1", InstrumentType.FIXED_RATE_BOND)
    store.add(inst)
    assert store.get("bond-1") is inst


def test_get_missing_raises_key_error(store: InstrumentStore) -> None:
    with pytest.raises(KeyError):
        store.get("nonexistent")


def test_by_type_returns_instruments_of_that_type(store: InstrumentStore) -> None:
    bond1 = _make_instrument("bond-1", InstrumentType.FIXED_RATE_BOND)
    bond2 = _make_instrument("bond-2", InstrumentType.FIXED_RATE_BOND)
    loan = _make_instrument("loan-1", InstrumentType.MORTGAGE)
    store.add(bond1)
    store.add(bond2)
    store.add(loan)

    bonds = store.by_type(InstrumentType.FIXED_RATE_BOND)
    assert len(bonds) == 2
    assert bond1 in bonds
    assert bond2 in bonds


def test_by_type_returns_empty_list_for_unknown_type(store: InstrumentStore) -> None:
    result = store.by_type(InstrumentType.CASH)
    assert result == []


def test_all_returns_all_instruments(store: InstrumentStore) -> None:
    inst1 = _make_instrument("inst-1", InstrumentType.FIXED_RATE_BOND)
    inst2 = _make_instrument("inst-2", InstrumentType.DEPOSIT)
    store.add(inst1)
    store.add(inst2)

    all_insts = store.all()
    assert len(all_insts) == 2
    assert inst1 in all_insts
    assert inst2 in all_insts


def test_all_returns_empty_when_store_empty(store: InstrumentStore) -> None:
    assert store.all() == []


def test_add_duplicate_overwrites(store: InstrumentStore) -> None:
    inst1 = _make_instrument("bond-1", InstrumentType.FIXED_RATE_BOND)
    inst2 = _make_instrument("bond-1", InstrumentType.FIXED_RATE_BOND)
    store.add(inst1)
    store.add(inst2)
    assert store.get("bond-1") is inst2
