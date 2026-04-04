"""SimulationService: drives the simulation forward (advance) and backward (step_back)."""

from __future__ import annotations

import itertools
from typing import TYPE_CHECKING

from brms.core.events import DateAdvanced, DateReverted, EventBus
from brms.core.models.history import DayRecord

if TYPE_CHECKING:
    import datetime

    from brms.core.models.accounting.rules.base import RuleRegistry
    from brms.core.models.accounting.service import AccountingService
    from brms.core.models.bank import Bank
    from brms.core.models.books import BankingBook, TradingBook
    from brms.core.models.history import SimulationHistory
    from brms.core.models.market_data import MarketDataStore, MarketState
    from brms.core.services.metrics_service import MetricsService


class SimulationService:
    """Orchestrates one-step-at-a-time simulation with full reversibility.

    Calling :meth:`advance` moves the simulation to the next available date,
    applies accounting rules, records metrics, and emits a :class:`DateAdvanced`
    event. Calling :meth:`step_back` undoes the most recent advance, reverses
    all posted transactions, restores book membership, and emits
    :class:`DateReverted`.
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
        """Advance the simulation by one date.

        Steps performed:
        1. Move to the next available market date.
        2. Build a :class:`DayRecord` with the current market state.
        3. Apply all accounting rules to every instrument in both books.
        4. Post generated transactions to the ledger.
        5. Compute all registered metrics.
        6. Push the day record onto the history stack.
        7. Emit a :class:`DateAdvanced` event.
        """
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
        """Reverse the most recent :meth:`advance`.

        Steps performed:
        1. Pop the most recent :class:`DayRecord` from the history stack.
        2. Decrement the date index.
        3. Restore instrument book membership (reverse order).
        4. Reverse all posted transactions (reverse order).
        5. Set :attr:`current_date` to the previous day's date, or None.
        6. Emit a :class:`DateReverted` event.
        """
        day_record: DayRecord = self._history.pop_day()
        self._date_index -= 1

        for change in reversed(day_record.instrument_changes):
            book = self._get_book(change.book_type)
            if change.action == "removed":
                book.add(change.instrument)
            elif change.action == "added":
                book.remove(change.instrument.id)

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
            f"SimulationService(bank={self._bank.name!r}, "
            f"current_date={self._current_date!r}, "
            f"date_index={self._date_index})"
        )
