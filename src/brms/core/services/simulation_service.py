"""SimulationService: thin V2 orchestrator that sequences service calls for each date."""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

from brms.core.events import DateAdvanced, DateReverted, EventBus, InstrumentAdded, InstrumentRemoved

if TYPE_CHECKING:
    import datetime

    from brms.core.models.bank import Bank
    from brms.core.models.market_data import MarketDataStore, MarketState
    from brms.core.models.transaction import Transaction
    from brms.core.rules.base import RuleRegistry
    from brms.core.services.accounting_service import AccountingService
    from brms.core.services.data_service import BankingBook, TradingBook
    from brms.core.services.metrics_service import MetricsService


# ---------------------------------------------------------------------------
# v1 history types (inlined; history.py has been removed)
# ---------------------------------------------------------------------------


@dataclass
class InstrumentChange:
    """Tracks an instrument addition or removal for reversal."""

    instrument: Any
    book_type: str
    action: Literal["added", "removed"]


@dataclass
class DayRecord:
    """All changes that occurred on a single simulation day."""

    date: datetime.date
    market_state: Any
    transactions: list[Transaction] = field(default_factory=list)
    instrument_changes: list[InstrumentChange] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)


class SimulationHistory:
    """Ordered stack of DayRecords supporting push/pop for step-back."""

    def __init__(self) -> None:
        """Initialise an empty history with no recorded days."""
        self._days: list[DayRecord] = []

    def push_day(self, record: DayRecord) -> None:
        """Append a new DayRecord, advancing the simulation by one day."""
        self._days.append(record)

    def pop_day(self) -> DayRecord:
        """Remove and return the most recent DayRecord, stepping the simulation back."""
        return self._days.pop()

    @property
    def current_day(self) -> DayRecord | None:
        """Return the most recent DayRecord, or None if history is empty."""
        return self._days[-1] if self._days else None

    @property
    def dates(self) -> list[datetime.date]:
        """Return the ordered list of dates present in history."""
        return [d.date for d in self._days]

    def get_series(
        self,
        metric_name: str,
        start: datetime.date | None = None,
        end: datetime.date | None = None,
    ) -> list[tuple[datetime.date, Any]]:
        """Return a time-series of (date, value) pairs for a given metric name.

        Optionally filter by *start* (inclusive) and *end* (inclusive) dates.
        Days that do not carry the requested metric are silently skipped.
        """
        result: list[tuple[datetime.date, Any]] = []
        for day in self._days:
            if start is not None and day.date < start:
                continue
            if end is not None and day.date > end:
                continue
            if metric_name in day.metrics:
                result.append((day.date, day.metrics[metric_name]))
        return result

    def get_snapshot(self, date: datetime.date) -> dict[str, Any] | None:
        """Return the metrics dict for a specific date, or None if not found."""
        for day in self._days:
            if day.date == date:
                return day.metrics
        return None

    def get_transactions(
        self,
        start: datetime.date | None = None,
        end: datetime.date | None = None,
    ) -> list[Transaction]:
        """Return all transactions across all days, optionally filtered by date range."""
        result: list[Transaction] = []
        for day in self._days:
            if start is not None and day.date < start:
                continue
            if end is not None and day.date > end:
                continue
            result.extend(day.transactions)
        return result


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


class LegacySimulationService:
    """Legacy V1 orchestrator with step-back support.

    Kept for reference; the application entry point (main.py) still wires this
    via keyword argument names from the old API.  New code should use
    :class:`SimulationService`.
    """

    def __init__(  # noqa: PLR0913
        self,
        bank: Bank,
        market_data: MarketDataStore,
        rule_registry: RuleRegistry,
        accounting_service: AccountingService,
        metrics_service: MetricsService,
        history: SimulationHistory,
        event_bus: EventBus,
    ) -> None:
        """Initialise the service with all required collaborators."""
        self._bank = bank
        self._market_data = market_data
        self._rules = rule_registry
        self._accounting = accounting_service
        self._metrics = metrics_service
        self._history = history
        self._events = event_bus
        self._available_dates: list[datetime.date] = market_data.available_dates()  # type: ignore[assignment]
        self._date_index: int = 0
        self._current_date: datetime.date | None = None

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def bank(self) -> Bank:
        """The bank being simulated."""
        return self._bank

    @property
    def current_date(self) -> datetime.date | None:
        """The date currently active in the simulation, or None before the first advance."""
        return self._current_date

    @property
    def start_date(self) -> datetime.date | None:
        """The earliest available simulation date, or None if no data loaded."""
        return self._available_dates[0] if self._available_dates else None

    @property
    def end_date(self) -> datetime.date | None:
        """The latest available simulation date, or None if no data loaded."""
        return self._available_dates[-1] if self._available_dates else None

    @property
    def market_data(self) -> MarketDataStore:
        """The underlying market data store."""
        return self._market_data

    @property
    def current_market_state(self) -> MarketState | None:
        """Zero-copy market state for the current date, or None before the first advance."""
        if self._current_date is None:
            return None
        return self._market_data.get_state(self._current_date)

    @property
    def history(self) -> SimulationHistory:
        """The accumulated simulation history."""
        return self._history

    # ------------------------------------------------------------------
    # Core simulation operations
    # ------------------------------------------------------------------

    def advance(self) -> None:
        """Advance the simulation by one date."""
        self._current_date = self._available_dates[self._date_index]
        self._date_index += 1

        market_state: MarketState = self._market_data.get_state(self._current_date)
        day_record = DayRecord(date=self._current_date, market_state=market_state)

        for instrument in itertools.chain(self._bank.banking_book, self._bank.trading_book):
            day_record.transactions.extend(
                self._rules.apply_all(instrument, market_state, self._current_date),
            )

        for tx in day_record.transactions:
            self._accounting.post(tx, self._bank.ledger)

        day_record.metrics = self._metrics.compute_all(self._bank, market_state, self._history)

        self._history.push_day(day_record)
        self._events.emit(DateAdvanced(self._current_date))

    def step_back(self) -> None:
        """Reverse the most recent :meth:`advance`."""
        day_record: DayRecord = self._history.pop_day()
        self._date_index -= 1

        for change in reversed(day_record.instrument_changes):
            book = self._get_book(change.book_type)
            if change.action == "removed":
                book.add(change.instrument)
                self._events.emit(InstrumentAdded(
                    instrument_id=change.instrument.id,
                    book_type=change.book_type,
                    instrument=change.instrument,
                ))
            elif change.action == "added":
                book.remove(change.instrument.id)
                self._events.emit(InstrumentRemoved(
                    instrument_id=change.instrument.id,
                    book_type=change.book_type,
                    instrument=change.instrument,
                ))

        for tx in reversed(day_record.transactions):
            self._accounting.reverse(tx, self._bank.ledger)

        prev = self._history.current_day
        self._current_date = prev.date if prev else None
        self._events.emit(DateReverted(day_record.date))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_book(self, book_type: str) -> BankingBook | TradingBook:
        """Return the banking or trading book for the given book_type string."""
        if book_type == "banking":
            return self._bank.banking_book
        return self._bank.trading_book

    def __repr__(self) -> str:  # noqa: D105
        return (
            f"LegacySimulationService(bank={self._bank.name!r}, "
            f"current_date={self._current_date!r}, "
            f"date_index={self._date_index})"
        )
