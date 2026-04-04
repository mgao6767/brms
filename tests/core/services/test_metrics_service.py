from unittest.mock import MagicMock

from brms.core.metrics.base import MetricRegistry
from brms.core.services.metrics_service import MetricsService


class PointMetric:
    name = "total_assets"
    requires_history = False

    def compute(self, bank, market_state, history=None):
        return 1_000_000


class HistMetric:
    name = "roa"
    requires_history = True

    def compute(self, bank, market_state, history=None):
        return 0.05 if history else None


def test_compute_all():
    reg = MetricRegistry()
    reg.register(PointMetric())
    reg.register(HistMetric())
    service = MetricsService(reg)
    results = service.compute_all(MagicMock(), MagicMock(), MagicMock())
    assert results["total_assets"] == 1_000_000
    assert results["roa"] == 0.05


def test_compute_one():
    reg = MetricRegistry()
    reg.register(PointMetric())
    service = MetricsService(reg)
    result = service.compute_one("total_assets", MagicMock(), MagicMock(), MagicMock())
    assert result == 1_000_000
