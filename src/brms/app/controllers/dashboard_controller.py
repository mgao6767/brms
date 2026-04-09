"""Controller for the dashboard view — subscribes to metrics and date events."""

from __future__ import annotations

from typing import TYPE_CHECKING

from brms.app.controllers.base import BRMSController
from brms.core.events import DateAdvanced, MetricsComputed, StatementsChanged

if TYPE_CHECKING:
    import datetime

    from brms.app.views.dashboard.dashboard_widget import BRMSDashboard
    from brms.core.events import EventBus
    from brms.core.models.accounting.ledger import Ledger
    from brms.core.services.reporting_service import ReportingService


class DashboardController(BRMSController):
    """Subscribes to MetricsComputed, StatementsChanged, DateAdvanced."""

    def __init__(  # noqa: PLR0913
        self,
        view: BRMSDashboard,
        event_bus: EventBus,
        reporting_service: ReportingService,
        ledger: Ledger,
        start_date: datetime.date | None = None,
        end_date: datetime.date | None = None,
    ) -> None:
        """Initialize the dashboard controller."""
        super().__init__()
        self.view = view
        self._reporting = reporting_service
        self._ledger = ledger
        self._start_date = start_date
        self._end_date = end_date
        self._dates: list[datetime.date] = []
        self._asset_values: list[float] = []
        self._liability_values: list[float] = []
        self._equity_values: list[float] = []
        self._cet1_ratio_values: list[float] = []

        event_bus.subscribe(DateAdvanced, self._on_date_advanced)
        event_bus.subscribe(MetricsComputed, self._on_metrics_computed)
        event_bus.subscribe(StatementsChanged, self._on_statements_changed)

    def init(self) -> None:
        """Initialize the dashboard view with starting state."""
        self.view.update_simulation_progress(0)
        if self._start_date:
            self.view.update_simulation_date(self._start_date)
            self.view.update_simulation_start_date(self._start_date)
        if self._end_date:
            self.view.update_simulation_end_date(self._end_date)
        self._refresh_plots()

    def update_speed(self, speed_label: str) -> None:
        """Update the speed label on the dashboard."""
        self.view.update_simulation_speed(speed_label)

    def _on_date_advanced(self, event: DateAdvanced) -> None:
        date = event.date
        self.view.update_simulation_date(date)
        if self._start_date and self._end_date and self._end_date > self._start_date:
            progress = (date - self._start_date) / (self._end_date - self._start_date) * 100
            self.view.update_simulation_progress(int(progress))

    def _on_metrics_computed(self, event: MetricsComputed) -> None:
        from brms.core.enums import MetricName

        m = event.metrics
        self._dates.append(event.date)
        self._asset_values.append(m.get(MetricName.TOTAL_ASSETS, 0.0))
        self._liability_values.append(m.get(MetricName.TOTAL_LIABILITIES, 0.0))
        self._equity_values.append(m.get(MetricName.TOTAL_EQUITY, 0.0))
        self._cet1_ratio_values.append(m.get(MetricName.CET1_RATIO, 0.0))
        self._refresh_plots()

    def _on_statements_changed(self, event: StatementsChanged) -> None:
        bs_data = self._reporting.balance_sheet(self._ledger, date=event.date)
        bs_data.setdefault("cet1", 0.0)
        bs_data.setdefault("cet1_ratio", 0.0)
        bs_data.setdefault("tier1_capital_ratio", 0.0)
        bs_data.setdefault("total_capital_ratio", 0.0)
        bs_data.setdefault("nsfr", 0.0)
        bs_data.setdefault("lcr", 0.0)
        self.view.update_bank_financials(bs_data)

    def _refresh_plots(self) -> None:
        self.view.update_assets_liabilities_plot(
            self._start_date,
            self._end_date,
            self._dates,
            self._asset_values,
            self._liability_values,
        )
        self.view.update_equity_plot(
            self._start_date,
            self._end_date,
            self._dates,
            self._equity_values,
        )
        self.view.update_capital_ratio_plot(
            self._start_date,
            self._end_date,
            self._dates,
            self._cet1_ratio_values,
        )
