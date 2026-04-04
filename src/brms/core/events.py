"""Core domain events and EventBus for publish-subscribe communication."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import datetime
    from collections.abc import Callable


class EventBus:
    """Publish-subscribe event bus. Core infrastructure, no framework dependencies."""

    def __init__(self) -> None:
        """Initialize with an empty handler registry."""
        self._handlers: dict[type, list[Callable]] = defaultdict(list)

    def subscribe(self, event_type: type, handler: Callable) -> None:
        """Register a handler for the given event type."""
        self._handlers[event_type].append(handler)

    def unsubscribe(self, event_type: type, handler: Callable) -> None:
        """Remove a previously registered handler for the given event type."""
        self._handlers[event_type].remove(handler)

    def emit(self, event: Any) -> None:  # noqa: ANN401
        """Dispatch an event to all registered handlers for its type."""
        for handler in self._handlers[type(event)]:
            handler(event)


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
