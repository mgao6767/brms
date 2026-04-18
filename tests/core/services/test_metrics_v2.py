"""Tests for V2 MetricsService writing to MetricStore."""

from __future__ import annotations

# ruff: noqa: S101, PLR2004
import datetime
from unittest.mock import MagicMock

from brms.core.enums import MetricName
from brms.core.metrics.base import MetricRegistry
from brms.core.services.metrics_service import MetricsService
from brms.core.stores.metric_store import MetricStore

_TOTAL_ASSETS = 1_000_000.0
_TOTAL_EQUITY = 250_000.0
_CET1_RATIO_V1 = 0.08
_CET1_RATIO_V2 = 0.10


class FakeMetric:  # noqa: D101
    name = MetricName.TOTAL_ASSETS

    def compute(self, bank, market_state, valuation_store, **kwargs) -> float:  # noqa: ANN001, ANN003, ARG002, D102
        return _TOTAL_ASSETS


class FakeMetricB:  # noqa: D101
    name = MetricName.TOTAL_EQUITY

    def compute(self, bank, market_state, valuation_store, **kwargs) -> float:  # noqa: ANN001, ANN003, ARG002, D102
        return _TOTAL_EQUITY


def test_compute_writes_to_metric_store() -> None:
    """compute() records the metric value in the store for the given date."""
    reg = MetricRegistry()
    reg.register(FakeMetric())
    service = MetricsService(reg)
    store = MetricStore()
    service.compute(MagicMock(), MagicMock(), datetime.date(2024, 1, 1), store, MagicMock())
    assert store.get(MetricName.TOTAL_ASSETS, datetime.date(2024, 1, 1)) == _TOTAL_ASSETS


def test_compute_multiple_metrics() -> None:
    """compute() writes all registered metrics to the store."""
    reg = MetricRegistry()
    reg.register(FakeMetric())
    reg.register(FakeMetricB())
    service = MetricsService(reg)
    store = MetricStore()
    date = datetime.date(2024, 6, 30)
    service.compute(MagicMock(), MagicMock(), date, store, MagicMock())
    assert store.get(MetricName.TOTAL_ASSETS, date) == _TOTAL_ASSETS
    assert store.get(MetricName.TOTAL_EQUITY, date) == _TOTAL_EQUITY


def test_compute_overwrites_on_same_date() -> None:
    """A second compute() call on the same date overwrites the stored value."""

    class MutableMetric:
        name = MetricName.CET1_RATIO
        value = _CET1_RATIO_V1

        def compute(self, bank, market_state, valuation_store, **kwargs) -> float:  # noqa: ANN001, ANN003, ARG002
            return self.value

    m = MutableMetric()
    reg = MetricRegistry()
    reg.register(m)
    service = MetricsService(reg)
    store = MetricStore()
    date = datetime.date(2024, 3, 1)

    service.compute(MagicMock(), MagicMock(), date, store, MagicMock())
    assert store.get(MetricName.CET1_RATIO, date) == _CET1_RATIO_V1

    m.value = _CET1_RATIO_V2
    service.compute(MagicMock(), MagicMock(), date, store, MagicMock())
    assert store.get(MetricName.CET1_RATIO, date) == _CET1_RATIO_V2


def test_compute_one_writes_and_returns() -> None:
    """compute_one() returns the value and writes it to the store."""
    reg = MetricRegistry()
    reg.register(FakeMetric())
    service = MetricsService(reg)
    store = MetricStore()
    date = datetime.date(2024, 12, 31)
    result = service.compute_one(MetricName.TOTAL_ASSETS, MagicMock(), MagicMock(), date, store, MagicMock())
    assert result == _TOTAL_ASSETS
    assert store.get(MetricName.TOTAL_ASSETS, date) == _TOTAL_ASSETS


def test_absent_date_returns_none() -> None:
    """Querying the store for an unrecorded date returns None."""
    reg = MetricRegistry()
    reg.register(FakeMetric())
    service = MetricsService(reg)
    store = MetricStore()
    service.compute(MagicMock(), MagicMock(), datetime.date(2024, 1, 1), store, MagicMock())
    assert store.get(MetricName.TOTAL_ASSETS, datetime.date(2024, 2, 1)) is None
