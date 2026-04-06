"""ValuationContext: long-lived mutable context updated once per valuation date."""

from __future__ import annotations

from typing import TYPE_CHECKING

import QuantLib as ql  # noqa: N813

from brms.core.services.yield_curve_service import YieldCurveService

if TYPE_CHECKING:
    import datetime


class ValuationContext:
    """Holds the shared valuation state (date, market data, term structure) for a single valuation run."""

    def __init__(self, yield_handle: ql.RelinkableYieldTermStructureHandle) -> None:
        """Initialise the context with a pre-created relinkable yield handle."""
        self._yield_handle = yield_handle
        self.market_data: object | None = None
        self.date: datetime.date | None = None

    def update(self, date: datetime.date, market_data: object) -> None:
        """Advance the context to *date* and rebuild the term structure from *market_data*.

        Sets the QuantLib global evaluation date, builds a new term structure from the
        market data yields, and relinks the shared handle so all downstream engines
        reprice automatically.
        """
        self.date = date
        self.market_data = market_data

        ql_date = ql.Date(date.day, date.month, date.year)
        ql.Settings.instance().evaluationDate = ql_date

        try:
            # market_data can be MarketDataStore or MarketState
            # Get yields: try .get_state(date).yields first, then .yields directly
            if hasattr(market_data, "get_state"):
                market_state = market_data.get_state(date)
                yields = market_state.yields
            else:
                yields = market_data.yields  # type: ignore[union-attr]
            maturity_labels = list(yields.index)
            rates = list(yields.values)
            term_structure = YieldCurveService.build_yield_curve(date, maturity_labels, rates)
            if term_structure is not None:
                self._yield_handle.linkTo(term_structure)
        except (AttributeError, KeyError):
            pass
