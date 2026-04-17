"""Core domain events and EventBus for publish-subscribe communication."""

from __future__ import annotations

from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import datetime
    from collections.abc import Callable, Generator
    from decimal import Decimal

    from brms.core.enums import MetricName
    from brms.core.models.transaction import Transaction


class EventBus:
    """Publish-subscribe event bus. Core infrastructure, no framework dependencies."""

    def __init__(self) -> None:
        """Initialize with an empty handler registry."""
        self._handlers: dict[type, list[Callable]] = defaultdict(list)
        self._batch_depth: int = 0
        self._queued: list = []

    def subscribe(self, event_type: type, handler: Callable) -> None:
        """Register a handler for the given event type."""
        self._handlers[event_type].append(handler)

    def unsubscribe(self, event_type: type, handler: Callable) -> None:
        """Remove a previously registered handler for the given event type."""
        self._handlers[event_type].remove(handler)

    def emit(self, event: Any) -> None:  # noqa: ANN401
        """Dispatch an event, or queue it if inside a batch context."""
        if self._batch_depth > 0:
            self._queued.append(event)
        else:
            self._dispatch(event)

    @contextmanager
    def batch(self) -> Generator[None, None, None]:
        """Queue events instead of dispatching. Flush on outermost exit."""
        self._batch_depth += 1
        try:
            yield
        finally:
            self._batch_depth -= 1
            if self._batch_depth == 0:
                self._flush()

    def _dispatch(self, event: Any) -> None:  # noqa: ANN401
        """Call all handlers for a single event."""
        for handler in self._handlers[type(event)]:
            handler(event)

    def _flush(self) -> None:
        """Dispatch all queued events in order, then clear the queue."""
        queued = self._queued
        self._queued = []
        for event in queued:
            self._dispatch(event)


# Domain events


@dataclass(frozen=True)
class DateAdvanced:
    """Event emitted when the simulation date is advanced forward."""

    date: datetime.date


@dataclass(frozen=True)
class DateReverted:
    """Event emitted when the simulation date is rolled back."""

    date: datetime.date


@dataclass(frozen=True)
class TransactionPosted:
    """Event emitted when a transaction is posted to the ledger."""

    transaction_id: str
    date: datetime.date


@dataclass(frozen=True)
class InstrumentMatured:
    """Event emitted when a financial instrument reaches maturity."""

    instrument_id: str
    date: datetime.date


@dataclass(frozen=True)
class InstrumentAdded:
    """Event emitted when an instrument is added to a book."""

    instrument_id: str
    book_type: str
    instrument: Any


@dataclass(frozen=True)
class InstrumentRemoved:
    """Event emitted when an instrument is removed from a book."""

    instrument_id: str
    book_type: str
    instrument: Any


@dataclass(frozen=True)
class ValuationsUpdated:
    """Event emitted after all positions have been valued for a date."""

    date: datetime.date
    valuations: dict[str, Decimal]  # position_id -> value


@dataclass(frozen=True)
class TransactionsRecorded:
    """Event emitted after transactions are posted and logged for a date."""

    date: datetime.date
    transactions: tuple[Transaction, ...]


@dataclass(frozen=True)
class MetricsComputed:
    """Event emitted after bank-level metrics are computed for a date."""

    date: datetime.date
    metrics: dict[MetricName, float]


@dataclass(frozen=True)
class StatementsChanged:
    """Event emitted after accounting entries change (statements need re-render)."""

    date: datetime.date


@dataclass(frozen=True)
class FinancialsUpdated:
    """Event emitted after financial statements have been computed for a date."""

    date: datetime.date
    total_assets: float
    total_liabilities: float
    total_equity: float


@dataclass(frozen=True)
class ShowTransactionsRequested:
    """Event emitted when the user requests to view transactions for an instrument."""

    instrument_id: str
