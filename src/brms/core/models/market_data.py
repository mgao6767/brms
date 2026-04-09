"""Market data store and zero-copy market state view."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

from brms.core.exceptions import ScenarioNotAvailableError

if TYPE_CHECKING:
    import datetime


class MarketDataStore:
    """Owns all market data as date-indexed DataFrames. Single source of truth."""

    def __init__(self) -> None:
        """Initialise an empty store."""
        self._frames: dict[str, pd.DataFrame] = {}

    def add_frame(self, name: str, df: pd.DataFrame) -> None:
        """Register a date-indexed DataFrame under the given name."""
        self._frames[name] = df

    def get_frame(self, name: str) -> pd.DataFrame:
        """Return the raw DataFrame for the given name."""
        return self._frames[name]

    def has_frame(self, name: str) -> bool:
        """Return True if a frame with the given name is registered."""
        return name in self._frames

    def get_state(self, date: datetime.date) -> MarketState:
        """Return a zero-copy MarketState view for the given date.

        Raises ScenarioNotAvailableError if any registered frame lacks data for that date.
        """
        ts = pd.Timestamp(date)
        for name, df in self._frames.items():
            if ts not in df.index:
                msg = f"No {name} data for {date}"
                raise ScenarioNotAvailableError(msg)
        return MarketState(date, self)

    def has_data(self, date: datetime.date) -> bool:
        """Return True if all registered frames have data for *date*."""
        if not self._frames:
            return False
        ts = pd.Timestamp(date)
        return all(ts in df.index for df in self._frames.values())

    def get_state_or_none(self, date: datetime.date) -> MarketState | None:
        """Return a MarketState for *date*, or None if data is missing."""
        if self.has_data(date):
            return MarketState(date, self)
        return None

    def available_dates(self) -> list[datetime.date]:
        """Return sorted list of dates present in all registered frames."""
        if not self._frames:
            return []
        sets = [set(df.index.date) for df in self._frames.values()]
        common = sets[0]
        for s in sets[1:]:
            common &= s
        return sorted(common)


class MarketState:
    """Zero-copy view into MarketDataStore for a specific date."""

    def __init__(self, date: datetime.date, store: MarketDataStore) -> None:
        """Initialise a view for *date* backed by *store*."""
        self._date = date
        self._store = store
        self._ts = pd.Timestamp(date)

    @property
    def date(self) -> datetime.date:
        """The date this state represents."""
        return self._date

    @property
    def yields(self) -> pd.Series:
        """Yield curve data as a Series (view, not copy)."""
        return self._store.get_frame("yields").loc[self._ts]

    @property
    def equity_prices(self) -> pd.Series:
        """Equity price data as a Series (view, not copy)."""
        return self._store.get_frame("equities").loc[self._ts]

    @property
    def fx_rates(self) -> pd.Series:
        """FX rate data as a Series (view, not copy)."""
        return self._store.get_frame("fx").loc[self._ts]

    def get(self, frame_name: str) -> pd.Series:
        """Return a row from the named frame for this state's date."""
        return self._store.get_frame(frame_name).loc[self._ts]
