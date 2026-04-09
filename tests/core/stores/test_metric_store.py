"""Tests for MetricStore."""

from __future__ import annotations

import datetime

import pytest

from brms.core.enums import MetricName
from brms.core.stores.metric_store import MetricStore


@pytest.fixture
def store() -> MetricStore:
    """Return a fresh MetricStore."""
    return MetricStore()


DATE_1 = datetime.date(2024, 1, 1)
DATE_2 = datetime.date(2024, 1, 2)
DATE_3 = datetime.date(2024, 1, 3)

RATIO_A = 0.10
RATIO_B = 0.12
RATIO_C = 0.14
RATIO_D = 0.15
LARGE_VALUE = 1_000_000


def test_record_and_get(store: MetricStore) -> None:
    """A recorded metric is retrievable by (name, date)."""
    store.record(MetricName.CET1_RATIO, DATE_1, RATIO_A)
    result = store.get(MetricName.CET1_RATIO, DATE_1)
    assert result == RATIO_A  # noqa: S101


def test_get_missing_metric_returns_none(store: MetricStore) -> None:
    """get() returns None for an unrecorded metric name."""
    result = store.get(MetricName.CET1_RATIO, DATE_1)
    assert result is None  # noqa: S101


def test_get_missing_date_returns_none(store: MetricStore) -> None:
    """get() returns None when no record exists for the given date."""
    store.record(MetricName.CET1_RATIO, DATE_1, RATIO_A)
    result = store.get(MetricName.CET1_RATIO, DATE_2)
    assert result is None  # noqa: S101


def test_series_full(store: MetricStore) -> None:
    """series() returns all (date, value) pairs sorted by date."""
    store.record(MetricName.CET1_RATIO, DATE_1, RATIO_A)
    store.record(MetricName.CET1_RATIO, DATE_2, RATIO_B)
    store.record(MetricName.CET1_RATIO, DATE_3, RATIO_C)

    result = store.series(MetricName.CET1_RATIO)
    assert result == [  # noqa: S101
        (DATE_1, RATIO_A),
        (DATE_2, RATIO_B),
        (DATE_3, RATIO_C),
    ]


def test_series_with_start(store: MetricStore) -> None:
    """series(start=...) excludes entries before the start date."""
    store.record(MetricName.CET1_RATIO, DATE_1, RATIO_A)
    store.record(MetricName.CET1_RATIO, DATE_2, RATIO_B)
    store.record(MetricName.CET1_RATIO, DATE_3, RATIO_C)

    result = store.series(MetricName.CET1_RATIO, start=DATE_2)
    assert result == [  # noqa: S101
        (DATE_2, RATIO_B),
        (DATE_3, RATIO_C),
    ]


def test_series_with_end(store: MetricStore) -> None:
    """series(end=...) excludes entries after the end date."""
    store.record(MetricName.CET1_RATIO, DATE_1, RATIO_A)
    store.record(MetricName.CET1_RATIO, DATE_2, RATIO_B)
    store.record(MetricName.CET1_RATIO, DATE_3, RATIO_C)

    result = store.series(MetricName.CET1_RATIO, end=DATE_2)
    assert result == [  # noqa: S101
        (DATE_1, RATIO_A),
        (DATE_2, RATIO_B),
    ]


def test_series_with_start_and_end(store: MetricStore) -> None:
    """series(start=..., end=...) returns only entries within the closed date range."""
    store.record(MetricName.CET1_RATIO, DATE_1, RATIO_A)
    store.record(MetricName.CET1_RATIO, DATE_2, RATIO_B)
    store.record(MetricName.CET1_RATIO, DATE_3, RATIO_C)

    result = store.series(MetricName.CET1_RATIO, start=DATE_2, end=DATE_2)
    assert result == [(DATE_2, RATIO_B)]  # noqa: S101


def test_series_missing_metric_returns_empty(store: MetricStore) -> None:
    """series() returns an empty list for an unrecorded metric name."""
    result = store.series(MetricName.CET1_RATIO)
    assert result == []  # noqa: S101


def test_series_sorted_by_date(store: MetricStore) -> None:
    """series() returns entries in ascending date order regardless of insertion order."""
    store.record(MetricName.CET1_RATIO, DATE_3, RATIO_C)
    store.record(MetricName.CET1_RATIO, DATE_1, RATIO_A)
    store.record(MetricName.CET1_RATIO, DATE_2, RATIO_B)

    result = store.series(MetricName.CET1_RATIO)
    dates = [r[0] for r in result]
    assert dates == sorted(dates)  # noqa: S101


def test_latest_returns_most_recent(store: MetricStore) -> None:
    """latest() returns the (date, value) pair with the most recent date."""
    store.record(MetricName.CET1_RATIO, DATE_1, RATIO_A)
    store.record(MetricName.CET1_RATIO, DATE_2, RATIO_B)
    store.record(MetricName.CET1_RATIO, DATE_3, RATIO_C)

    result = store.latest(MetricName.CET1_RATIO)
    assert result == (DATE_3, RATIO_C)  # noqa: S101


def test_latest_single_entry(store: MetricStore) -> None:
    """latest() returns the only entry when there is just one."""
    store.record(MetricName.CET1_RATIO, DATE_1, RATIO_A)
    result = store.latest(MetricName.CET1_RATIO)
    assert result == (DATE_1, RATIO_A)  # noqa: S101


def test_latest_empty_returns_none(store: MetricStore) -> None:
    """latest() returns None for an unrecorded metric name."""
    result = store.latest(MetricName.CET1_RATIO)
    assert result is None  # noqa: S101


def test_multiple_metrics_independent(store: MetricStore) -> None:
    """Different metric names maintain independent time series."""
    store.record(MetricName.CET1_RATIO, DATE_1, RATIO_D)
    store.record(MetricName.TOTAL_ASSETS, DATE_1, LARGE_VALUE)

    assert store.get(MetricName.CET1_RATIO, DATE_1) == RATIO_D  # noqa: S101
    assert store.get(MetricName.TOTAL_ASSETS, DATE_1) == LARGE_VALUE  # noqa: S101
    assert store.get(MetricName.LEVERAGE_RATIO, DATE_1) is None  # noqa: S101
