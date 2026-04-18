"""Metric protocol and MetricRegistry for the BRMS bank simulation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    import datetime
    from collections.abc import Iterable

    from brms.core.enums import MetricName
    from brms.core.models.market_data import MarketState
    from brms.core.stores.valuation_store import ValuationStore


@runtime_checkable
class Metric(Protocol):
    """Protocol defining the interface for a computable bank metric."""

    name: MetricName

    def compute(
        self,
        bank: Any,  # noqa: ANN401
        market_state: MarketState,
        valuation_store: ValuationStore,
        date: datetime.date | None = None,
    ) -> Any:  # noqa: ANN401
        """Compute the metric value."""
        ...


class MetricRegistry:
    """Registry for Metric instances, keyed by MetricName."""

    def __init__(self, metrics: Iterable[Metric] = ()) -> None:  # noqa: D107
        self._metrics: dict[MetricName, Metric] = {m.name: m for m in metrics}

    def register(self, metric: Metric) -> None:
        """Register a metric."""
        self._metrics[metric.name] = metric

    def get(self, name: MetricName) -> Metric:
        """Retrieve a metric by name."""
        return self._metrics[name]

    def all_metrics(self) -> list[Metric]:
        """Return all registered metrics."""
        return list(self._metrics.values())
