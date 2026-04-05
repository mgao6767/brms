"""Tests for ValuationStore."""

from __future__ import annotations

import datetime
from decimal import Decimal

import pytest

from brms.core.enums import ValuationType
from brms.core.stores.valuation_store import ValuationStore


@pytest.fixture
def store() -> ValuationStore:
    """Return a fresh ValuationStore."""
    return ValuationStore()


DATE_1 = datetime.date(2024, 1, 1)
DATE_2 = datetime.date(2024, 1, 2)
DATE_3 = datetime.date(2024, 1, 3)


def test_record_and_get(store: ValuationStore) -> None:
    """A recorded valuation is retrievable by (position_id, date, type)."""
    store.record("pos-1", DATE_1, ValuationType.FAIR_VALUE, Decimal("100.00"))
    result = store.get("pos-1", DATE_1, ValuationType.FAIR_VALUE)
    assert result == Decimal("100.00")  # noqa: S101


def test_get_missing_returns_none(store: ValuationStore) -> None:
    """get() returns None for an unknown position_id."""
    result = store.get("pos-nonexistent", DATE_1, ValuationType.FAIR_VALUE)
    assert result is None  # noqa: S101


def test_get_missing_date_returns_none(store: ValuationStore) -> None:
    """get() returns None when no record exists for the given date."""
    store.record("pos-1", DATE_1, ValuationType.FAIR_VALUE, Decimal("100.00"))
    result = store.get("pos-1", DATE_2, ValuationType.FAIR_VALUE)
    assert result is None  # noqa: S101


def test_get_missing_valuation_type_returns_none(store: ValuationStore) -> None:
    """get() returns None when no record exists for the given valuation type."""
    store.record("pos-1", DATE_1, ValuationType.FAIR_VALUE, Decimal("100.00"))
    result = store.get("pos-1", DATE_1, ValuationType.CARRYING_VALUE)
    assert result is None  # noqa: S101


def test_series_full(store: ValuationStore) -> None:
    """series() returns all (date, value) pairs sorted by date."""
    store.record("pos-1", DATE_1, ValuationType.FAIR_VALUE, Decimal("100.00"))
    store.record("pos-1", DATE_2, ValuationType.FAIR_VALUE, Decimal("101.00"))
    store.record("pos-1", DATE_3, ValuationType.FAIR_VALUE, Decimal("102.00"))

    result = store.series("pos-1", ValuationType.FAIR_VALUE)
    assert result == [  # noqa: S101
        (DATE_1, Decimal("100.00")),
        (DATE_2, Decimal("101.00")),
        (DATE_3, Decimal("102.00")),
    ]


def test_series_with_start(store: ValuationStore) -> None:
    """series(start=...) excludes entries before the start date."""
    store.record("pos-1", DATE_1, ValuationType.FAIR_VALUE, Decimal("100.00"))
    store.record("pos-1", DATE_2, ValuationType.FAIR_VALUE, Decimal("101.00"))
    store.record("pos-1", DATE_3, ValuationType.FAIR_VALUE, Decimal("102.00"))

    result = store.series("pos-1", ValuationType.FAIR_VALUE, start=DATE_2)
    assert result == [  # noqa: S101
        (DATE_2, Decimal("101.00")),
        (DATE_3, Decimal("102.00")),
    ]


def test_series_with_end(store: ValuationStore) -> None:
    """series(end=...) excludes entries after the end date."""
    store.record("pos-1", DATE_1, ValuationType.FAIR_VALUE, Decimal("100.00"))
    store.record("pos-1", DATE_2, ValuationType.FAIR_VALUE, Decimal("101.00"))
    store.record("pos-1", DATE_3, ValuationType.FAIR_VALUE, Decimal("102.00"))

    result = store.series("pos-1", ValuationType.FAIR_VALUE, end=DATE_2)
    assert result == [  # noqa: S101
        (DATE_1, Decimal("100.00")),
        (DATE_2, Decimal("101.00")),
    ]


def test_series_with_start_and_end(store: ValuationStore) -> None:
    """series(start=..., end=...) returns only entries within the closed date range."""
    store.record("pos-1", DATE_1, ValuationType.FAIR_VALUE, Decimal("100.00"))
    store.record("pos-1", DATE_2, ValuationType.FAIR_VALUE, Decimal("101.00"))
    store.record("pos-1", DATE_3, ValuationType.FAIR_VALUE, Decimal("102.00"))

    result = store.series("pos-1", ValuationType.FAIR_VALUE, start=DATE_2, end=DATE_2)
    assert result == [(DATE_2, Decimal("101.00"))]  # noqa: S101


def test_series_missing_position_returns_empty(store: ValuationStore) -> None:
    """series() returns an empty list for an unknown position_id."""
    result = store.series("nonexistent", ValuationType.FAIR_VALUE)
    assert result == []  # noqa: S101


def test_series_sorted_by_date(store: ValuationStore) -> None:
    """series() returns entries in ascending date order regardless of insertion order."""
    store.record("pos-1", DATE_3, ValuationType.FAIR_VALUE, Decimal("102.00"))
    store.record("pos-1", DATE_1, ValuationType.FAIR_VALUE, Decimal("100.00"))
    store.record("pos-1", DATE_2, ValuationType.FAIR_VALUE, Decimal("101.00"))

    result = store.series("pos-1", ValuationType.FAIR_VALUE)
    dates = [r[0] for r in result]
    assert dates == sorted(dates)  # noqa: S101


def test_snapshot(store: ValuationStore) -> None:
    """snapshot() returns a dict of position_id to value for a given date and type."""
    store.record("pos-1", DATE_1, ValuationType.FAIR_VALUE, Decimal("100.00"))
    store.record("pos-2", DATE_1, ValuationType.FAIR_VALUE, Decimal("200.00"))
    store.record("pos-3", DATE_2, ValuationType.FAIR_VALUE, Decimal("300.00"))

    result = store.snapshot(DATE_1, ValuationType.FAIR_VALUE)
    assert result == {  # noqa: S101
        "pos-1": Decimal("100.00"),
        "pos-2": Decimal("200.00"),
    }


def test_snapshot_empty_date_returns_empty_dict(store: ValuationStore) -> None:
    """snapshot() returns an empty dict when no records exist for the given date."""
    result = store.snapshot(DATE_1, ValuationType.FAIR_VALUE)
    assert result == {}  # noqa: S101


def test_record_overwrites_existing(store: ValuationStore) -> None:
    """record() overwrites a previously stored value for the same key."""
    store.record("pos-1", DATE_1, ValuationType.FAIR_VALUE, Decimal("100.00"))
    store.record("pos-1", DATE_1, ValuationType.FAIR_VALUE, Decimal("999.00"))
    assert store.get("pos-1", DATE_1, ValuationType.FAIR_VALUE) == Decimal("999.00")  # noqa: S101
