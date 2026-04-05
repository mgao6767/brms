"""Tests for ValuationStore."""

from __future__ import annotations

import datetime
from decimal import Decimal

import pytest

from brms.core.enums import ValuationType
from brms.core.stores.valuation_store import ValuationStore


@pytest.fixture()
def store() -> ValuationStore:
    return ValuationStore()


DATE_1 = datetime.date(2024, 1, 1)
DATE_2 = datetime.date(2024, 1, 2)
DATE_3 = datetime.date(2024, 1, 3)


def test_record_and_get(store: ValuationStore) -> None:
    store.record("pos-1", DATE_1, ValuationType.FAIR_VALUE, Decimal("100.00"))
    result = store.get("pos-1", DATE_1, ValuationType.FAIR_VALUE)
    assert result == Decimal("100.00")


def test_get_missing_returns_none(store: ValuationStore) -> None:
    result = store.get("pos-nonexistent", DATE_1, ValuationType.FAIR_VALUE)
    assert result is None


def test_get_missing_date_returns_none(store: ValuationStore) -> None:
    store.record("pos-1", DATE_1, ValuationType.FAIR_VALUE, Decimal("100.00"))
    result = store.get("pos-1", DATE_2, ValuationType.FAIR_VALUE)
    assert result is None


def test_get_missing_valuation_type_returns_none(store: ValuationStore) -> None:
    store.record("pos-1", DATE_1, ValuationType.FAIR_VALUE, Decimal("100.00"))
    result = store.get("pos-1", DATE_1, ValuationType.CARRYING_VALUE)
    assert result is None


def test_series_full(store: ValuationStore) -> None:
    store.record("pos-1", DATE_1, ValuationType.FAIR_VALUE, Decimal("100.00"))
    store.record("pos-1", DATE_2, ValuationType.FAIR_VALUE, Decimal("101.00"))
    store.record("pos-1", DATE_3, ValuationType.FAIR_VALUE, Decimal("102.00"))

    result = store.series("pos-1", ValuationType.FAIR_VALUE)
    assert result == [
        (DATE_1, Decimal("100.00")),
        (DATE_2, Decimal("101.00")),
        (DATE_3, Decimal("102.00")),
    ]


def test_series_with_start(store: ValuationStore) -> None:
    store.record("pos-1", DATE_1, ValuationType.FAIR_VALUE, Decimal("100.00"))
    store.record("pos-1", DATE_2, ValuationType.FAIR_VALUE, Decimal("101.00"))
    store.record("pos-1", DATE_3, ValuationType.FAIR_VALUE, Decimal("102.00"))

    result = store.series("pos-1", ValuationType.FAIR_VALUE, start=DATE_2)
    assert result == [
        (DATE_2, Decimal("101.00")),
        (DATE_3, Decimal("102.00")),
    ]


def test_series_with_end(store: ValuationStore) -> None:
    store.record("pos-1", DATE_1, ValuationType.FAIR_VALUE, Decimal("100.00"))
    store.record("pos-1", DATE_2, ValuationType.FAIR_VALUE, Decimal("101.00"))
    store.record("pos-1", DATE_3, ValuationType.FAIR_VALUE, Decimal("102.00"))

    result = store.series("pos-1", ValuationType.FAIR_VALUE, end=DATE_2)
    assert result == [
        (DATE_1, Decimal("100.00")),
        (DATE_2, Decimal("101.00")),
    ]


def test_series_with_start_and_end(store: ValuationStore) -> None:
    store.record("pos-1", DATE_1, ValuationType.FAIR_VALUE, Decimal("100.00"))
    store.record("pos-1", DATE_2, ValuationType.FAIR_VALUE, Decimal("101.00"))
    store.record("pos-1", DATE_3, ValuationType.FAIR_VALUE, Decimal("102.00"))

    result = store.series("pos-1", ValuationType.FAIR_VALUE, start=DATE_2, end=DATE_2)
    assert result == [(DATE_2, Decimal("101.00"))]


def test_series_missing_position_returns_empty(store: ValuationStore) -> None:
    result = store.series("nonexistent", ValuationType.FAIR_VALUE)
    assert result == []


def test_series_sorted_by_date(store: ValuationStore) -> None:
    # Insert out of order
    store.record("pos-1", DATE_3, ValuationType.FAIR_VALUE, Decimal("102.00"))
    store.record("pos-1", DATE_1, ValuationType.FAIR_VALUE, Decimal("100.00"))
    store.record("pos-1", DATE_2, ValuationType.FAIR_VALUE, Decimal("101.00"))

    result = store.series("pos-1", ValuationType.FAIR_VALUE)
    dates = [r[0] for r in result]
    assert dates == sorted(dates)


def test_snapshot(store: ValuationStore) -> None:
    store.record("pos-1", DATE_1, ValuationType.FAIR_VALUE, Decimal("100.00"))
    store.record("pos-2", DATE_1, ValuationType.FAIR_VALUE, Decimal("200.00"))
    store.record("pos-3", DATE_2, ValuationType.FAIR_VALUE, Decimal("300.00"))  # different date

    result = store.snapshot(DATE_1, ValuationType.FAIR_VALUE)
    assert result == {
        "pos-1": Decimal("100.00"),
        "pos-2": Decimal("200.00"),
    }


def test_snapshot_empty_date_returns_empty_dict(store: ValuationStore) -> None:
    result = store.snapshot(DATE_1, ValuationType.FAIR_VALUE)
    assert result == {}


def test_record_overwrites_existing(store: ValuationStore) -> None:
    store.record("pos-1", DATE_1, ValuationType.FAIR_VALUE, Decimal("100.00"))
    store.record("pos-1", DATE_1, ValuationType.FAIR_VALUE, Decimal("999.00"))
    assert store.get("pos-1", DATE_1, ValuationType.FAIR_VALUE) == Decimal("999.00")
