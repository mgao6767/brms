"""MetricStore: time-series store for bank-level metrics."""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import datetime

    from brms.core.enums import MetricName


class MetricStore:
    """Stores scalar metric values keyed by (MetricName, date)."""

    def __init__(self) -> None:
        """Initialize an empty metric store."""
        # MetricName -> list of (date, value) tuples (insertion order)
        self._data: dict[MetricName, list[tuple[datetime.date, Any]]] = defaultdict(list)
        # For O(1) point lookup: MetricName -> date -> list index
        self._index: dict[MetricName, dict[datetime.date, int]] = defaultdict(dict)

    def record(self, name: MetricName, date: datetime.date, value: Any) -> None:  # noqa: ANN401
        """Record a metric value. If the date already exists, overwrites in place."""
        idx_map = self._index[name]
        if date in idx_map:
            i = idx_map[date]
            self._data[name][i] = (date, value)
        else:
            entries = self._data[name]
            idx_map[date] = len(entries)
            entries.append((date, value))

    def get(self, name: MetricName, date: datetime.date) -> Any | None:  # noqa: ANN401
        """Return the value for *name* on *date*, or None if absent."""
        idx_map = self._index.get(name)
        if idx_map is None:
            return None
        i = idx_map.get(date)
        if i is None:
            return None
        return self._data[name][i][1]

    def series(
        self,
        name: MetricName,
        start: datetime.date | None = None,
        end: datetime.date | None = None,
    ) -> list[tuple[datetime.date, Any]]:
        """Return (date, value) pairs sorted by date, optionally bounded by start/end."""
        entries = self._data.get(name)
        if not entries:
            return []

        result = sorted(entries, key=lambda t: t[0])
        if start is not None:
            result = [(d, v) for d, v in result if d >= start]
        if end is not None:
            result = [(d, v) for d, v in result if d <= end]
        return result

    def latest(self, name: MetricName) -> tuple[datetime.date, Any] | None:
        """Return the (date, value) pair with the most recent date, or None if empty."""
        entries = self._data.get(name)
        if not entries:
            return None
        return max(entries, key=lambda t: t[0])
