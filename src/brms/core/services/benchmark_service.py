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
        """Initialise with a fresh PrimeIndex and no synced state.

        Prime is forecast off *forwarding_handle* (the Treasury curve) plus a basis spread set
        from the latest Prime fixing at each sync, so forecasts start at today's Prime instead
        of the Treasury short rate.
        """
        self._base_handle = forwarding_handle
        self._basis = ql.SimpleQuote(0.0)
        forwarding = None
        if forwarding_handle is not None:
            spreaded = ql.ZeroSpreadedTermStructure(forwarding_handle, ql.QuoteHandle(self._basis))
            spreaded.enableExtrapolation()
            forwarding = ql.YieldTermStructureHandle(spreaded)
        self._prime_index = PrimeIndex(forwarding=forwarding)
        self._last_synced_date: datetime.date | None = None
        self._last_fixing: float | None = None

    @property
    def curve_handle(self) -> ql.RelinkableYieldTermStructureHandle:
        """The discount-curve handle Prime is forecast from (the engine must link this one)."""
        if self._base_handle is None:
            msg = "This BenchmarkService was built without a curve handle"
            raise ValueError(msg)
        return self._base_handle

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

        self._sync_fixings(date, benchmarks)
        self._update_basis(date)

    def _update_basis(self, date: datetime.date) -> None:
        """Set the forecast basis to the latest Prime fixing less the curve's one-month zero rate."""
        if self._base_handle is None or self._last_fixing is None:
            return
        qd = ql.Date(date.day, date.month, date.year)
        try:
            treasury = self._base_handle.zeroRate(qd + ql.Period(1, ql.Months), ql.Actual365Fixed(), ql.Continuous)
        except RuntimeError:
            return  # no curve linked yet (before the first market-data day)
        self._basis.setValue(self._last_fixing - treasury.rate())

    def _sync_fixings(self, date: datetime.date, benchmarks: pd.DataFrame) -> None:
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

        calendar = self._prime_index.fixingCalendar()
        ql_dates = []
        ql_rates = []
        for d, r in zip(new_rows.index, new_rows.to_numpy(), strict=False):
            qd = ql.Date(d.day, d.month, d.year)
            if calendar.isBusinessDay(qd):
                ql_dates.append(qd)
                ql_rates.append(float(r) / 100.0)
        if not ql_dates:
            self._last_synced_date = date
            return
        self._prime_index.addFixings(ql_dates, ql_rates, forceOverwrite=True)
        self._last_fixing = ql_rates[-1]
        self._last_synced_date = date

    def reset(self) -> None:
        """Clear QL's fixing history for this index. For test isolation."""
        ql.IndexManager.instance().clearHistory(self._prime_index.name())
        self._last_synced_date = None
