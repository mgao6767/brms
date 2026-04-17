"""BenchmarkService: syncs Prime fixings from MarketDataStore into QL's IndexManager."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd
import QuantLib as ql  # noqa: N813

from brms.core.models.benchmarks import PrimeIndex

if TYPE_CHECKING:
    import datetime

    from brms.core.models.market_data import MarketDataStore


class BenchmarkService:
    """Keeps the QL PrimeIndex fixing history in sync with MarketDataStore.

    The MarketDataStore is authoritative. This service projects the 'benchmarks'
    frame into QL's global IndexManager, one-way and incrementally.
    """

    _PRIME_COLUMN = "DPRIME"

    def __init__(self, forwarding_handle: ql.YieldTermStructureHandle | None = None) -> None:
        """Initialise with a fresh PrimeIndex and no synced state."""
        self._prime_index = PrimeIndex(forwarding=forwarding_handle)
        self._last_synced_date: datetime.date | None = None

    @property
    def prime_index(self) -> PrimeIndex:
        """The shared PrimeIndex instance whose fixings this service manages."""
        return self._prime_index

    def sync_up_to(self, date: datetime.date, market_data: MarketDataStore) -> None:
        """Append fixings from the store that aren't yet in the QL index."""
        if not market_data.has_frame("benchmarks"):
            return
        benchmarks = market_data.get_frame("benchmarks")
        if self._PRIME_COLUMN not in benchmarks.columns:
            return

        ts = pd.Timestamp(date)
        if self._last_synced_date is None:
            mask = benchmarks.index <= ts
        else:
            last_ts = pd.Timestamp(self._last_synced_date)
            mask = (benchmarks.index > last_ts) & (benchmarks.index <= ts)

        new_rows = benchmarks.loc[mask, self._PRIME_COLUMN].dropna()
        if new_rows.empty:
            self._last_synced_date = date
            return

        ql_dates = [ql.Date(d.day, d.month, d.year) for d in new_rows.index]
        ql_rates = [float(r) / 100.0 for r in new_rows.to_numpy()]
        self._prime_index.addFixings(ql_dates, ql_rates, forceOverwrite=True)
        self._last_synced_date = date

    def reset(self) -> None:
        """Clear QL's fixing history for this index. For test isolation."""
        ql.IndexManager.instance().clearHistory(self._prime_index.name())
        self._last_synced_date = None
