"""ValuationService: strategy-based valuation dispatching by InstrumentClass."""

from __future__ import annotations

from typing import TYPE_CHECKING

import QuantLib as ql  # noqa: N813

from brms.core.enums import InstrumentClass, PositionStatus
from brms.core.services.valuation_context import ValuationContext

if TYPE_CHECKING:
    import datetime

    from brms.core.models.bank import Bank
    from brms.core.models.market_data import MarketDataStore
    from brms.core.services.valuation_strategies import ValuationStrategy
    from brms.core.stores.valuation_store import ValuationStore


class ValuationService:
    """Strategy-based valuation service (V2) dispatching by InstrumentClass.

    A single :class:`ValuationContext` is shared across all strategies to avoid
    rebuilding the term structure multiple times per date.
    """

    def __init__(self, strategies: dict[InstrumentClass, ValuationStrategy] | None = None) -> None:
        """Initialise with an optional strategy mapping and a shared context."""
        self._yield_handle: ql.RelinkableYieldTermStructureHandle = ql.RelinkableYieldTermStructureHandle()
        self._strategies: dict[InstrumentClass, ValuationStrategy] = dict(strategies) if strategies else {}
        self._context: ValuationContext = ValuationContext(self._yield_handle)

    def register_strategy(self, instrument_class: InstrumentClass, strategy: ValuationStrategy) -> None:
        """Register *strategy* for positions of *instrument_class*."""
        self._strategies[instrument_class] = strategy

    def value_all(
        self,
        bank: Bank,
        market_data: MarketDataStore,
        date: datetime.date,
        valuation_store: ValuationStore,
    ) -> None:
        """Value all open positions in *bank*, grouped by InstrumentClass.

        Updates the shared context once for *date*, then delegates to each registered
        strategy for its corresponding InstrumentClass, skipping empty batches.
        """
        self._context.update(date, market_data)
        for instrument_class, strategy in self._strategies.items():
            positions = bank.positions.query(  # type: ignore[union-attr]
                instrument_class=instrument_class,
                status=PositionStatus.OPEN,
            )
            if positions:
                strategy.value_batch(positions, bank.instruments, self._context, valuation_store)  # type: ignore[union-attr]
