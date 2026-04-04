"""Metric protocol and MetricRegistry for the BRMS bank simulation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from brms.core.models.history import SimulationHistory
    from brms.core.models.market_data import MarketState


@runtime_checkable
class Metric(Protocol):
    """Protocol defining the interface for a computable bank metric."""

    name: str
    requires_history: bool

    def compute(
        self,
        bank: Any,  # noqa: ANN401
        market_state: MarketState,
        history: SimulationHistory | None = None,
    ) -> Any:  # noqa: ANN401
        """Compute the metric value."""
        ...


class MetricRegistry:
    """Registry for Metric instances, keyed by name."""

    def __init__(self) -> None:  # noqa: D107
        self._metrics: dict[str, Metric] = {}

    def register(self, metric: Metric) -> None:
        """Register a metric."""
        self._metrics[metric.name] = metric

    def get(self, name: str) -> Metric:
        """Retrieve a metric by name."""
        return self._metrics[name]

    def all_metrics(self) -> list[Metric]:
        """Return all registered metrics."""
        return list(self._metrics.values())
