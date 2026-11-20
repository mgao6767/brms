"""ValuationContext: long-lived mutable context updated once per valuation date."""

from __future__ import annotations

from typing import TYPE_CHECKING

import QuantLib as ql  # noqa: N813

from brms.core.exceptions import ValuationError
from brms.core.services.yield_curve_service import YieldCurveService

if TYPE_CHECKING:
    import datetime

    from brms.core.models.market_data import MarketDataStore
    from brms.core.services.benchmark_service import BenchmarkService


class ValuationContext:
    """Holds the shared valuation state (date, market data, term structure) for a single valuation run."""

    def __init__(
        self,
        yield_handle: ql.RelinkableYieldTermStructureHandle,
        benchmark_service: BenchmarkService | None = None,
    ) -> None:
        """Initialise the context with a pre-created relinkable yield handle."""
        self._yield_handle = yield_handle
        self._benchmark_service = benchmark_service
        self.market_data: MarketDataStore | None = None
        self.date: datetime.date | None = None
        self.has_market_data: bool = False

    @property
    def yield_handle(self) -> ql.RelinkableYieldTermStructureHandle:
        """The shared discounting handle, relinked to each market day's curve."""
        return self._yield_handle

    def update(self, date: datetime.date, market_data: MarketDataStore, *, has_market_data: bool = True) -> None:
        """Advance the context to *date*; on market-data days rebuild the term structure.

        Every day this sets the QuantLib global evaluation date and syncs benchmark fixings.
        On a market-data day it also builds the curve from the day's yields and relinks the
        shared handle so that downstream engines reprice. A curve that cannot be built is an
        error, never a stale curve.
        """
        self.date = date
        self.market_data = market_data
        self.has_market_data = has_market_data

        # Every day, market data or not: floating-rate coupons need the evaluation date and
        # the benchmark fixings (which come from their own frame, not from the yields). On a
        # market day the fixings are synced after the new curve is linked, because the Prime
        # forecast basis is measured against it.
        ql.Settings.instance().evaluationDate = ql.Date(date.day, date.month, date.year)
        if not has_market_data:
            if self._benchmark_service is not None:
                self._benchmark_service.sync_up_to(date, market_data)
            return

        try:
            state = market_data.get_state(date) if hasattr(market_data, "get_state") else market_data
            yields = state.yields  # type: ignore[union-attr]
            term_structure = YieldCurveService.build_yield_curve(date, list(yields.index), list(yields.values))
        except (AttributeError, KeyError, ValueError, RuntimeError) as exc:
            msg = f"Cannot build the yield curve for {date}: {exc}"
            raise ValuationError(msg) from exc
        if term_structure is None:
            msg = f"No yields to build the curve for {date}"
            raise ValuationError(msg)
        self._yield_handle.linkTo(term_structure)
        if self._benchmark_service is not None:
            self._benchmark_service.sync_up_to(date, market_data)
