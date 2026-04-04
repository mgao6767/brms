"""MetricsService: computes bank metrics via a MetricRegistry."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from brms.core.metrics.base import MetricRegistry
    from brms.core.models.history import SimulationHistory
    from brms.core.models.market_data import MarketState


class MetricsService:
    """Service for computing bank metrics via a MetricRegistry."""

    def __init__(self, metric_registry: MetricRegistry) -> None:  # noqa: D107
        self._registry = metric_registry

    def compute_all(
        self,
        bank: Any,  # noqa: ANN401
        market_state: MarketState,
        history: SimulationHistory,
    ) -> dict[str, Any]:
        """Compute all registered metrics and return as a name→value dict."""
        results: dict[str, Any] = {}
        for metric in self._registry.all_metrics():
            history_arg = history if metric.requires_history else None
            results[metric.name] = metric.compute(bank, market_state, history_arg)
        return results

    def compute_one(
        self,
        name: str,
        bank: Any,  # noqa: ANN401
        market_state: MarketState,
        history: SimulationHistory,
    ) -> Any:  # noqa: ANN401
        """Compute a single metric by name."""
        metric = self._registry.get(name)
        history_arg = history if metric.requires_history else None
        return metric.compute(bank, market_state, history_arg)
