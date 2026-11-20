"""ValuationService: strategy-based valuation dispatching by MeasurementBasis."""

from __future__ import annotations

from typing import TYPE_CHECKING

import QuantLib as ql  # noqa: N813

from brms.core.enums import MeasurementBasis, PositionStatus
from brms.core.services.valuation_context import ValuationContext

if TYPE_CHECKING:
    import datetime

    from brms.core.models.bank import Bank
    from brms.core.models.market_data import MarketDataStore
    from brms.core.services.benchmark_service import BenchmarkService
    from brms.core.services.valuation_strategies import ValuationStrategy
    from brms.core.stores.valuation_store import ValuationStore


class ValuationService:
    """Strategy-based valuation service dispatching by MeasurementBasis.

    A single :class:`ValuationContext` is shared across all strategies to avoid
    rebuilding the term structure multiple times per date.
    """

    def __init__(
        self,
        strategies: dict[MeasurementBasis, ValuationStrategy] | None = None,
        benchmark_service: BenchmarkService | None = None,
        yield_handle: ql.RelinkableYieldTermStructureHandle | None = None,
    ) -> None:
        """Initialise with an optional strategy mapping and a shared context."""
        # An empty handle is falsy in QuantLib, so test for None explicitly.
        self._yield_handle = yield_handle if yield_handle is not None else ql.RelinkableYieldTermStructureHandle()
        self._strategies: dict[MeasurementBasis, ValuationStrategy] = dict(strategies) if strategies else {}
        self._context: ValuationContext = ValuationContext(self._yield_handle, benchmark_service=benchmark_service)

    @property
    def yield_handle(self) -> ql.RelinkableYieldTermStructureHandle:
        """The shared discount and forwarding handle, linked to the latest market day's curve."""
        return self._yield_handle

    def prepare(self, date: datetime.date, market_data: MarketDataStore) -> None:
        """Link the curve of the last market day on or before *date* (and sync fixings), recording nothing.

        Used after loading a snapshot so that a first simulated day without market data (a weekend
        or holiday) still has a curve for floating-rate forecasts.
        """
        days = [d for d in market_data.available_dates() if d <= date]
        if days:
            self._context.update(days[-1], market_data, has_market_data=True)
        self._context.update(date, market_data, has_market_data=False)

    def register_strategy(self, measurement_basis: MeasurementBasis, strategy: ValuationStrategy) -> None:
        """Register *strategy* for positions of *measurement_basis*."""
        self._strategies[measurement_basis] = strategy

    def value_all(
        self,
        bank: Bank,
        market_data: MarketDataStore,
        date: datetime.date,
        valuation_store: ValuationStore,
        *,
        has_market_data: bool = True,
    ) -> None:
        """Value all open positions in *bank*, grouped by MeasurementBasis.

        Updates the shared context once for *date* (rebuilding the curve only on market-data
        days), then delegates to each registered strategy for its MeasurementBasis.
        """
        self._context.update(date, market_data, has_market_data=has_market_data)
        for measurement_basis, strategy in self._strategies.items():
            positions = bank.positions.query(  # type: ignore[union-attr]
                measurement_basis=measurement_basis,
                status=PositionStatus.OPEN,
            )
            if positions:
                strategy.value_batch(positions, bank.instruments, self._context, valuation_store)  # type: ignore[union-attr]
