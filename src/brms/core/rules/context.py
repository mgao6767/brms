"""RuleContext: pre-packaged state passed to every accounting rule."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import datetime

    from brms.core.models.market_data import MarketState
    from brms.core.models.position import Position
    from brms.core.stores.valuation_store import ValuationStore


class RuleContext:
    """Everything a rule needs to make decisions, pre-packaged for convenience.

    Created once per advance() call by the RuleEngine and passed to every rule.
    """

    def __init__(
        self,
        date: datetime.date,
        previous_date: datetime.date | None,
        market_state: MarketState | None,
        valuation_store: ValuationStore,
        market_data: MarketState | None = None,
        *,
        has_market_data: bool = True,
    ) -> None:
        """Initialise the context with date, market state, and valuation data."""
        self.date = date
        self.previous_date = previous_date
        self.market_state = market_state
        self.valuation_store = valuation_store
        self.market_data = market_data
        self.has_market_data = has_market_data

    def position_previous_date(self, position: Position) -> datetime.date:
        """Return the date a position's accrual is measured from today.

        That is the engine's previous date, but never earlier than the acquisition
        date: a position acquired at close of business on its acquisition date
        earns nothing before it.
        """
        if self.previous_date is None:
            return position.acquisition_date
        return max(self.previous_date, position.acquisition_date)
