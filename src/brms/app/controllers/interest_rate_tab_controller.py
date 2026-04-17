"""Controller for the Interest Rate tab — table + time-series plot of benchmark rates."""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

from brms.app.controllers.base import BRMSController
from brms.app.models.interest_rate_model import InterestRateModel
from brms.core.events import DateAdvanced

if TYPE_CHECKING:
    from brms.app.views.interest_rate import BRMSInterestRateWidget
    from brms.core.events import EventBus
    from brms.core.models.market_data import MarketDataStore


class InterestRateTabController(BRMSController):
    """Drives the Interest Rate tab: populates the table and extends the time-series plot."""

    def __init__(
        self,
        view: BRMSInterestRateWidget,
        event_bus: EventBus,
        market_data: MarketDataStore,
        start_date: datetime.date | None = None,
        end_date: datetime.date | None = None,
    ) -> None:
        super().__init__()
        self.view = view
        self._event_bus = event_bus
        self._market_data = market_data
        self._start_date = start_date
        self._end_date = end_date

        self.model = InterestRateModel()
        self.view.set_model(self.model)

        self._plot_dates: list[datetime.date] = []
        self._plot_values: dict[str, list[float]] = {"Prime": []}
        self._plots_dirty = False

        self._event_bus.subscribe(DateAdvanced, self._on_date_advanced)
        self.view.visibility_changed.connect(self._flush_if_dirty)

    def reset(self) -> None:
        self.model.blockSignals(True)
        self.model.reset()
        self.model.blockSignals(False)
        self._plot_dates.clear()
        self._plot_values = {"Prime": []}
        self.view.plot_widget.clear_plot()

    def init(self) -> None:
        """Populate the table from the benchmarks frame and hide future rows."""
        if self._market_data.has_frame("benchmarks"):
            self.model.update_from_dataframe(self._market_data.get_frame("benchmarks"))
            self._hide_future_rows(None)

    def _on_date_advanced(self, event: DateAdvanced) -> None:
        self._hide_future_rows(event.date)
        self._append_rate(event.date)
        if self.view.is_visible:
            self._refresh_plot()
        else:
            self._plots_dirty = True

    def _append_rate(self, date: datetime.date) -> None:
        """Read the Prime rate for *date* from the market data store and append."""
        if not self._market_data.has_frame("benchmarks"):
            return
        try:
            state = self._market_data.get_state(date)
            prime = float(state.benchmarks["DPRIME"])
        except (KeyError, Exception):
            return
        self._plot_dates.append(date)
        self._plot_values["Prime"].append(prime)

    def _refresh_plot(self) -> None:
        if not self._plot_dates or self._start_date is None:
            return
        self.view.plot_widget.update_plot(self._start_date, self._plot_dates, self._plot_values)
        self._plots_dirty = False

    def _flush_if_dirty(self) -> None:
        if self._plots_dirty and self.view.is_visible:
            self._refresh_plot()

    def on_visible(self) -> None:
        if self._plots_dirty:
            self._refresh_plot()

    def _hide_future_rows(self, current_date: datetime.date | None) -> None:
        dates = self.model.reference_dates()
        for i, d in enumerate(dates):
            hidden = current_date is None or d > current_date
            self.view.table_view.setRowHidden(i, hidden)
