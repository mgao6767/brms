"""Tests for MetricRegistry."""

from __future__ import annotations

# ruff: noqa: S101
from brms.core.enums import MetricName
from brms.core.metrics.base import MetricRegistry


class FakeMetric:  # noqa: D101
    name = MetricName.TOTAL_ASSETS

    def compute(self, bank, market_state, valuation_store) -> int:  # noqa: ANN001, ARG002, D102
        return 42


def test_register_and_get() -> None:
    """MetricRegistry stores and retrieves metrics by MetricName."""
    reg = MetricRegistry()
    m = FakeMetric()
    reg.register(m)
    assert reg.get(MetricName.TOTAL_ASSETS) is m


def test_all_metrics() -> None:
    """all_metrics returns all registered metrics as a list."""
    reg = MetricRegistry()
    reg.register(FakeMetric())
    assert len(reg.all_metrics()) == 1
