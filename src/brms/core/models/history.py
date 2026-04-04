"""SimulationHistory: ordered stack of DayRecords supporting push/pop for step-back."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    import datetime

    from brms.core.models.transaction import Transaction


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
    """Ordered stack of DayRecords. Supports push (advance) and pop (step-back)."""

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
