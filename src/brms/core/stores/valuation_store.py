"""ValuationStore: time-series store for position valuations."""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import datetime
    from decimal import Decimal

    from brms.core.enums import ValuationType


class ValuationStore:
    """Stores valuation records keyed by (position_id, date, valuation_type)."""

    def __init__(self) -> None:
        """Initialize an empty valuation store."""
        # position_id -> date -> ValuationType -> Decimal
        self._data: dict[str, dict[datetime.date, dict[ValuationType, Decimal]]] = defaultdict(
            lambda: defaultdict(dict),
        )

    def record(
        self,
        position_id: str,
        date: datetime.date,
        valuation_type: ValuationType,
        value: Decimal,
    ) -> None:
        """Store a valuation value. Overwrites if already present."""
        self._data[position_id][date][valuation_type] = value

    def get(
        self,
        position_id: str,
        date: datetime.date,
        valuation_type: ValuationType,
    ) -> Decimal | None:
        """Return the stored value or None if absent."""
        return self._data.get(position_id, {}).get(date, {}).get(valuation_type)

    def series(
        self,
        position_id: str,
        valuation_type: ValuationType,
        start: datetime.date | None = None,
        end: datetime.date | None = None,
    ) -> list[tuple[datetime.date, Decimal]]:
        """Return (date, value) pairs sorted by date, optionally bounded by start/end."""
        date_map = self._data.get(position_id)
        if not date_map:
            return []

        result: list[tuple[datetime.date, Decimal]] = []
        for date, type_map in date_map.items():
            if start is not None and date < start:
                continue
            if end is not None and date > end:
                continue
            value = type_map.get(valuation_type)
            if value is not None:
                result.append((date, value))

        result.sort(key=lambda t: t[0])
        return result

    def get_previous(
        self,
        position_id: str,
        date: datetime.date,
        valuation_type: ValuationType,
    ) -> Decimal | None:
        """Return the most recent value strictly before *date*, or None if absent."""
        date_map = self._data.get(position_id)
        if not date_map:
            return None
        prior_dates = sorted(d for d in date_map if d < date)
        for prior_date in reversed(prior_dates):
            val = date_map[prior_date].get(valuation_type)
            if val is not None:
                return val
        return None

    def snapshot(
        self,
        date: datetime.date,
        valuation_type: ValuationType,
    ) -> dict[str, Decimal]:
        """Return {position_id: value} for all positions with a record on *date*."""
        result: dict[str, Decimal] = {}
        for position_id, date_map in self._data.items():
            value = date_map.get(date, {}).get(valuation_type)
            if value is not None:
                result[position_id] = value
        return result
