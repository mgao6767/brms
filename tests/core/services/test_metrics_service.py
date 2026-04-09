"""Tests for MetricsService (v2: writes to MetricStore)."""

from __future__ import annotations

# ruff: noqa: S101, PLR2004
import datetime
from unittest.mock import MagicMock

from brms.core.enums import MetricName
from brms.core.metrics.base import MetricRegistry
from brms.core.services.metrics_service import MetricsService
from brms.core.stores.metric_store import MetricStore

_ASSETS = 1_000_000
_EQUITY = 200_000


class PointMetric:  # noqa: D101
    name = MetricName.TOTAL_ASSETS

    def compute(self, bank, market_state, valuation_store) -> int:  # noqa: ANN001, ARG002, D102
        return _ASSETS


class EquityMetric:  # noqa: D101
    name = MetricName.TOTAL_EQUITY

    def compute(self, bank, market_state, valuation_store) -> int:  # noqa: ANN001, ARG002, D102
        return _EQUITY


def test_compute_writes_all_metrics() -> None:
    """compute() writes all metric values to the store."""
    reg = MetricRegistry()
    reg.register(PointMetric())
    reg.register(EquityMetric())
    service = MetricsService(reg)
    store = MetricStore()
    date = datetime.date(2024, 1, 1)
    service.compute(MagicMock(), MagicMock(), date, store, MagicMock())
    assert store.get(MetricName.TOTAL_ASSETS, date) == _ASSETS
    assert store.get(MetricName.TOTAL_EQUITY, date) == _EQUITY


def test_compute_one() -> None:
    """compute_one() writes a single metric and returns its value."""
    reg = MetricRegistry()
    reg.register(PointMetric())
    service = MetricsService(reg)
    store = MetricStore()
    date = datetime.date(2024, 1, 1)
    result = service.compute_one(MetricName.TOTAL_ASSETS, MagicMock(), MagicMock(), date, store, MagicMock())
    assert result == _ASSETS
    assert store.get(MetricName.TOTAL_ASSETS, date) == _ASSETS
