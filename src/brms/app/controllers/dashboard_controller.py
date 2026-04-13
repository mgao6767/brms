"""Controller for the dashboard view — subscribes to metrics and date events."""

from __future__ import annotations

from typing import TYPE_CHECKING

from brms.app.controllers.base import BRMSController
from brms.core.enums import MetricName
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

        # Plot data series — keyed by line title
        self._dates: list[datetime.date] = []
        self._series: dict[str, list[float]] = {
            "Total Assets": [],
            "Total Liabilities": [],
            "Total Equity": [],
            "CET1 Ratio": [],
            "NSFR": [],
            "LCR": [],
            "NIM": [],
            "ROA": [],
            "ROE": [],
        }

        # Map MetricName → (line title for series, KPI card attribute on view)
        self._metric_to_line: dict[MetricName, str] = {
            MetricName.TOTAL_ASSETS: "Total Assets",
            MetricName.TOTAL_LIABILITIES: "Total Liabilities",
            MetricName.TOTAL_EQUITY: "Total Equity",
            MetricName.CET1_RATIO: "CET1 Ratio",
        }

        self._plots_dirty = False
        self._financials_dirty = False
        self._last_financials_date: datetime.date | None = None

        event_bus.subscribe(DateAdvanced, self._on_date_advanced)
        event_bus.subscribe(MetricsComputed, self._on_metrics_computed)
        event_bus.subscribe(StatementsChanged, self._on_statements_changed)

    def init(self) -> None:
        """Initialize the dashboard view with starting state."""
        self.view.sim_strip.set_progress(0)
        if self._start_date:
            self.view.sim_strip.set_date(self._start_date)
        if self._start_date and self._end_date:
            self.view.sim_strip.set_period(self._start_date, self._end_date)
        self._refresh_plots()

    def on_visible(self) -> None:
        """Flush deferred plot and financial updates when the dashboard becomes visible."""
        if self._plots_dirty:
            self._refresh_plots()
            self._plots_dirty = False
        if self._financials_dirty and self._last_financials_date is not None:
            self._update_financials(self._last_financials_date)
            self._financials_dirty = False

    def _on_date_advanced(self, event: DateAdvanced) -> None:
        date = event.date
        self.view.sim_strip.set_date(date)
        if self._start_date and self._end_date and self._end_date > self._start_date:
            progress = (date - self._start_date) / (self._end_date - self._start_date) * 100
            self.view.sim_strip.set_progress(int(progress))

    def _on_metrics_computed(self, event: MetricsComputed) -> None:
        m = event.metrics
        self._dates.append(event.date)

        # Append to series
        self._series["Total Assets"].append(m.get(MetricName.TOTAL_ASSETS, 0.0))
        self._series["Total Liabilities"].append(m.get(MetricName.TOTAL_LIABILITIES, 0.0))
        self._series["Total Equity"].append(m.get(MetricName.TOTAL_EQUITY, 0.0))
        self._series["CET1 Ratio"].append(m.get(MetricName.CET1_RATIO, 0.0))

        # Update balance sheet group card
        self.view.balance_sheet_group.set_value("total_assets", m.get(MetricName.TOTAL_ASSETS))
        self.view.balance_sheet_group.set_value("total_liabilities", m.get(MetricName.TOTAL_LIABILITIES))
        self.view.balance_sheet_group.set_value("total_equity", m.get(MetricName.TOTAL_EQUITY))

        # Update group card metrics from MetricsComputed
        self.view.capital_group.set_value("cet1_capital", m.get(MetricName.CET1_CAPITAL))
        self.view.capital_group.set_value("cet1_ratio", m.get(MetricName.CET1_RATIO))
        self.view.liquidity_group.set_value("credit_rwa", m.get(MetricName.CREDIT_RWA))
        self.view.liquidity_group.set_value("op_rwa", m.get(MetricName.OPERATIONAL_RWA))
        self.view.profit_group.set_value("nim", m.get(MetricName.NET_INTEREST_MARGIN))
        self.view.profit_group.set_value("roa", m.get(MetricName.ROA))
        self.view.profit_group.set_value("roe", m.get(MetricName.ROE))
        self.view.profit_group.set_value("leverage_ratio", m.get(MetricName.LEVERAGE_RATIO))

        if self.view.isVisible():
            self._refresh_plots()
        else:
            self._plots_dirty = True

    def _on_statements_changed(self, event: StatementsChanged) -> None:
        self._last_financials_date = event.date
        if self.view.isVisible():
            self._update_financials(event.date)
        else:
            self._financials_dirty = True

    def _update_financials(self, date: datetime.date) -> None:
        bs_data = self._reporting.balance_sheet(self._ledger, date=date)

        # Update group card metrics that come from balance sheet
        self.view.capital_group.set_value("tier1_ratio", bs_data.get("tier1_capital_ratio"))
        self.view.capital_group.set_value("total_capital_ratio", bs_data.get("total_capital_ratio"))
        self.view.liquidity_group.set_value("nsfr", bs_data.get("nsfr"))
        self.view.liquidity_group.set_value("lcr", bs_data.get("lcr"))

    def _refresh_plots(self) -> None:
        s, e, d = self._start_date, self._end_date, self._dates

        # Balance sheet (3 lines in one chart)
        self.view.balance_sheet_plot.update_plot(s, e, d, {
            "Total Assets": self._series["Total Assets"],
            "Total Liabilities": self._series["Total Liabilities"],
            "Total Equity": self._series["Total Equity"],
        })

        # Capital ratios
        self.view.capital_ratio_plot.update_plot(s, e, d, {
            "CET1 Ratio": self._series["CET1 Ratio"],
        })

        # Liquidity (series may be empty until wired)
        if self._series["NSFR"] or self._series["LCR"]:
            self.view.liquidity_plot.update_plot(s, e, d, {
                "NSFR": self._series["NSFR"],
                "LCR": self._series["LCR"],
            })

        # Profitability (series may be empty until wired)
        if self._series["NIM"] or self._series["ROA"] or self._series["ROE"]:
            self.view.profitability_plot.update_plot(s, e, d, {
                "NIM": self._series["NIM"],
                "ROA": self._series["ROA"],
                "ROE": self._series["ROE"],
            })
