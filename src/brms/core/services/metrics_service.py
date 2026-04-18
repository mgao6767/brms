"""MetricsService: computes bank metrics and writes results to MetricStore."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import datetime

    from brms.core.enums import MetricName
    from brms.core.metrics.base import MetricRegistry
    from brms.core.models.market_data import MarketState
    from brms.core.stores.metric_store import MetricStore
    from brms.core.stores.valuation_store import ValuationStore


class MetricsService:
    """Service for computing bank metrics via a MetricRegistry."""

    def __init__(self, metric_registry: MetricRegistry) -> None:  # noqa: D107
        self._registry = metric_registry

    def compute(
        self,
        bank: Any,  # noqa: ANN401
        market_state: MarketState,
        date: datetime.date,
        metric_store: MetricStore,
        valuation_store: ValuationStore,
    ) -> None:
        """Compute all registered metrics and write results to metric_store."""
        for metric in self._registry.all_metrics():
            value = metric.compute(bank, market_state, valuation_store, date=date)
            metric_store.record(metric.name, date, value)

    def compute_all(
        self,
        bank: Any,  # noqa: ANN401
        market_state: Any,  # noqa: ANN401
        history: Any,  # noqa: ANN401, ARG002
    ) -> dict[str, Any]:
        """Legacy compute_all: compute all metrics and return as a dict (no store needed)."""
        results: dict[str, Any] = {}
        for metric in self._registry.all_metrics():
            results[metric.name.name] = metric.compute(bank, market_state, None)
        return results

    def compute_one(  # noqa: PLR0913
        self,
        name: MetricName,
        bank: Any,  # noqa: ANN401
        market_state: MarketState,
        date: datetime.date,
        metric_store: MetricStore,
        valuation_store: ValuationStore,
    ) -> Any:  # noqa: ANN401
        """Compute a single metric by name and write it to metric_store."""
        metric = self._registry.get(name)
        value = metric.compute(bank, market_state, valuation_store, date=date)
        metric_store.record(metric.name, date, value)
        return value
