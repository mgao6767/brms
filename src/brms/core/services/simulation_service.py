"""SimulationService: thin orchestrator that sequences service calls for each date."""

from __future__ import annotations

from typing import TYPE_CHECKING

from brms.core.events import DateAdvanced, EventBus

if TYPE_CHECKING:
    import datetime


class SimulationService:
    """Thin V2 orchestrator: sequences service calls for each simulation date.

    Calling :meth:`advance` moves the simulation to the given date by running
    valuation, rule application, accounting, metrics, and emitting
    :class:`DateAdvanced`.  No step-back support — history is external.
    """

    def __init__(  # noqa: PLR0913
        self,
        bank: object,
        market_data: object,
        valuation_service: object,
        rule_engine: object,
        accounting_service: object,
        metrics_service: object,
        valuation_store: object,
        metric_store: object,
        transaction_log: object,
        event_bus: EventBus,
    ) -> None:
        """Initialise the orchestrator with all required collaborators."""
        self.bank = bank
        self.market_data = market_data
        self.valuation_service = valuation_service
        self.rule_engine = rule_engine
        self.accounting_service = accounting_service
        self.metrics_service = metrics_service
        self.valuation_store = valuation_store
        self.metric_store = metric_store
        self.transaction_log = transaction_log
        self.event_bus = event_bus
        self._current_date: datetime.date | None = None  # type: ignore[name-defined]
        self._end_date: datetime.date | None = None  # type: ignore[name-defined]
        # Derive end date from available market data
        available = self.market_data.available_dates()
        if available:
            self._end_date = available[-1]

    @property
    def current_date(self) -> datetime.date | None:  # type: ignore[name-defined]
        """The most recently advanced date, or None."""
        return self._current_date

    def advance(self, date: datetime.date | None = None) -> None:  # type: ignore[name-defined]
        """Advance the simulation by one calendar day (or to an explicit *date*).

        Steps performed (in order):
        1. Determine the target date (next calendar day or explicit).
        2. Fetch market state if available for this date.
        3. Value all positions (only on market-data days).
        4. Apply rules via the rule engine to obtain transactions.
        5. Post all transactions to the ledger via the accounting service.
        6. Record the transaction batch in the transaction log.
        7. Compute metrics (only on market-data days).
        8. Emit :class:`DateAdvanced`.
        """
        from datetime import timedelta

        if date is None:
            if self._current_date is None:
                available = self.market_data.available_dates()
                if not available:
                    msg = "No market data available"
                    raise IndexError(msg)
                date = available[0]
            else:
                date = self._current_date + timedelta(days=1)

        # Lazily resolve end date from market data (may not be available at construction)
        if self._end_date is None:
            available = self.market_data.available_dates()
            if available:
                self._end_date = available[-1]

        if self._end_date and date > self._end_date:
            msg = "Past end date"
            raise IndexError(msg)

        previous_date = self._current_date
        self._current_date = date
        has_market = self.market_data.has_data(date)
        market_state = self.market_data.get_state_or_none(date)

        if has_market:
            self.valuation_service.value_all(self.bank, self.market_data, date, self.valuation_store)

        transactions = self.rule_engine.apply(
            self.bank, self.valuation_store, market_state, date, previous_date,
            has_market_data=has_market,
        )
        self.accounting_service.post_all(transactions, self.bank.ledger, self.bank.positions)
        self.transaction_log.record_batch(transactions)

        if has_market and market_state is not None:
            self.metrics_service.compute(self.bank, market_state, date, self.metric_store, self.valuation_store)

        self.event_bus.emit(DateAdvanced(date))

    def __repr__(self) -> str:  # noqa: D105
        return f"SimulationService(bank={self.bank!r})"
