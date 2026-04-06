"""Main controller module for the BRMS application."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import QTimer

from brms.app.controllers.bank_controller import BankController
from brms.app.controllers.base import BRMSController
from brms.app.controllers.inspector_controller import InspectorController
from brms.app.controllers.yield_curve_controller import YieldCurveController

if TYPE_CHECKING:
    import datetime

    from brms.app.views.main_window import MainWindow
    from brms.core.events import DateAdvanced
    from brms.core.services.simulation_service import SimulationService

logger = logging.getLogger(__name__)


class MainController(BRMSController):
    """Main controller class for the Simulation."""

    def __init__(
        self,
        view: MainWindow,
        *,
        core_services: dict[str, Any] | None = None,
    ) -> None:
        """Initialize the MainController."""
        super().__init__()
        self.view: MainWindow = view  # type: ignore[annotation-unchecked]

        # Store core services for future use as migration progresses
        self._core: dict[str, Any] = core_services or {}
        self._simulation_service: SimulationService | None = self._core.get("simulation_service")

        # Derive start/end dates from SimulationService
        self._start_date: datetime.date | None = None
        self._end_date: datetime.date | None = None
        if self._simulation_service is not None:
            dates = self._simulation_service.market_data.available_dates()
            if dates:
                self._start_date = dates[0]
                self._end_date = dates[-1]

        # Subscribe to EventBus DateAdvanced events for view updates
        if self._simulation_service is not None:
            from brms.core.events import DateAdvanced, EventBus

            event_bus: EventBus | None = self._core.get("event_bus")
            if event_bus is not None:
                event_bus.subscribe(DateAdvanced, self._on_date_advanced)

        # Initialize the timer
        self.simulation_base_interval = 500
        self.simulation_interval = self.simulation_base_interval
        self.simulation_timer = QTimer()
        self.simulation_timer.setInterval(self.simulation_interval)
        # Sub controllers
        core_bank = self._simulation_service.bank if self._simulation_service else None
        self.inspector_ctrl = InspectorController(inspector_widget=self.view.inspector_widget)
        self.bank_ctrl = BankController(
            bank=core_bank,
            event_bus=self._core.get("event_bus"),
            reporting_service=self._core.get("reporting_service"),
            banking_book_view=self.view.banking_book_widget,
            trading_book_view=self.view.trading_book_widget,
            inspector_ctrl=self.inspector_ctrl,
            statement_view=self.view.statement_viewer_widget,
        )
        self.yield_curve_ctrl = YieldCurveController(view=self.view.yield_curve_widget)
        # Connect signals
        self.connect_signals()
        # Initial tasks
        self.bank_ctrl.update_statement()
        QTimer.singleShot(100, self.init)

    def connect_signals(self) -> None:
        """Connect signals from the view to the controller's slots."""
        self.simulation_timer.timeout.connect(self.on_advance)
        self.view.next_action.triggered.connect(self.on_advance)
        self.view.start_action.triggered.connect(self.on_start_action)
        self.view.pause_action.triggered.connect(self.on_pause_action)
        self.view.stop_action.triggered.connect(self.on_stop_action)
        self.view.speed_up_action.triggered.connect(self.on_speed_up_action)
        self.view.speed_down_action.triggered.connect(self.on_speed_down_action)
        self.view.exit_signal.connect(self.on_exit)

        self.bank_ctrl.bank_financials_updated.connect(self.view.dashboard.update_bank_financials)

    def init(self) -> None:
        """Initialize the simulation and set the starting scenario.

        These should be init actions on a fresh simulation start.
        """
        # Initialize yield curve controller with market data if available
        if self._simulation_service is not None:
            market_data = self._simulation_service.market_data
            if market_data.has_frame("yields"):
                yields_df = market_data.get_frame("yields")
                self.yield_curve_ctrl.init_from_dataframe(yields_df)

        # Set up dashboard dates
        self.view.dashboard.update_simulation_progress(0)
        if self._start_date is not None:
            self.view.dashboard.update_simulation_date(self._start_date)
            self.view.dashboard.update_simulation_start_date(self._start_date)
        if self._end_date is not None:
            self.view.dashboard.update_simulation_end_date(self._end_date)
        self.update_dashboard()
        # misc
        if self._start_date is not None:
            self.view.transaction_history_widget.set_end_date(self._start_date)
            self.view.transaction_history_widget.set_start_date(self._start_date)

    def on_exit(self) -> None:
        """Handle the exit signal from the view."""
        self.view.close()

    def update_dashboard(self) -> None:
        """Refresh all dashboard plots using MetricStore time-series data."""
        metric_store = self._core.get("metric_store")
        if metric_store:
            from brms.core.enums import MetricName

            asset_series = metric_store.series(MetricName.TOTAL_ASSETS)
            dates = [d for d, _ in asset_series]
            asset_values = [v for _, v in asset_series]
            liability_series = metric_store.series(MetricName.TOTAL_LIABILITIES)
            liability_values = [v for _, v in liability_series]
            equity_series = metric_store.series(MetricName.TOTAL_EQUITY)
            equity_values = [v for _, v in equity_series]
            cet1_series = metric_store.series(MetricName.CET1_RATIO)
            cet1_values = [v for _, v in cet1_series]
        else:
            dates, asset_values, liability_values, equity_values, cet1_values = [], [], [], [], []

        self.view.dashboard.update_assets_liabilities_plot(
            start=self._start_date,
            end=self._end_date,
            dates=dates,
            asset_values=asset_values,
            liability_values=liability_values,
        )
        self.view.dashboard.update_equity_plot(
            start=self._start_date,
            end=self._end_date,
            dates=dates,
            equity_values=equity_values,
        )
        self.view.dashboard.update_capital_ratio_plot(
            start=self._start_date,
            end=self._end_date,
            dates=dates,
            values=cet1_values,
        )

    def on_advance(self) -> None:
        """Advance simulation by one step using SimulationService."""
        if self._simulation_service is None:
            logger.warning("on_advance called but SimulationService is not available.")
            return
        try:
            self._simulation_service.advance()
        except IndexError:
            logger.info("No more dates available in SimulationService; pausing.")
            self.on_pause_action()

    def step_back(self) -> None:
        """Step the simulation back by one day using SimulationService."""
        if self._simulation_service is None:
            logger.warning("step_back called but SimulationService is not available.")
            return
        try:
            self._simulation_service.step_back()
        except IndexError:
            logger.info("No history to step back through.")

    def _on_date_advanced(self, event: DateAdvanced) -> None:
        """Handle DateAdvanced events from the EventBus to update UI."""
        date = event.date
        self.view.statusBar().showMessage(f"Current date: {date}")
        self.view.dashboard.update_simulation_date(date)
        if self._start_date and self._end_date and self._end_date > self._start_date:
            progress = (date - self._start_date) / (self._end_date - self._start_date) * 100
            self.view.dashboard.update_simulation_progress(int(progress))
        self.bank_ctrl.update_statement(date)
        self.update_dashboard()

        # Push today's transactions to the history widget
        transaction_log = self._core.get("transaction_log")
        if transaction_log:
            for tx in transaction_log.by_date(date):
                self.view.transaction_history_widget.add_transaction(tx)

    def on_start_action(self) -> None:
        """Start the simulation timer for continuous advancement."""
        self.view.next_action.setDisabled(True)
        self.view.start_action.setDisabled(True)
        self.view.pause_action.setEnabled(True)
        self.view.stop_action.setEnabled(True)
        self.simulation_timer.start()

    def on_pause_action(self) -> None:
        """Pause the simulation timer."""
        self.view.next_action.setEnabled(True)
        self.view.start_action.setEnabled(True)
        self.view.pause_action.setDisabled(True)
        self.view.stop_action.setDisabled(True)
        self.simulation_timer.stop()

    def on_stop_action(self) -> None:
        """Stop the simulation and disable all controls."""
        self.view.next_action.setDisabled(True)
        self.view.start_action.setDisabled(True)
        self.view.pause_action.setDisabled(True)
        self.view.stop_action.setDisabled(True)
        self.simulation_timer.stop()

    def on_speed_up_action(self) -> None:
        """Increase the simulation speed by 0.5x."""
        current_speed = self.simulation_base_interval / self.simulation_timer.interval()
        current_speed = round(current_speed, 1)
        _min_speed = 0.1
        _max_speed = 5.0
        new_speed = 0.5 if current_speed == _min_speed else min(_max_speed, current_speed + 0.5)
        self.simulation_interval = int(self.simulation_base_interval / new_speed)
        self.simulation_timer.setInterval(self.simulation_interval)
        self.view.dashboard.update_simulation_speed(f"{new_speed:.1f}x")

    def on_speed_down_action(self) -> None:
        """Decrease the simulation speed by 0.5x."""
        current_speed = self.simulation_base_interval / self.simulation_timer.interval()
        current_speed = round(current_speed, 1)
        _min_speed = 0.1
        new_speed = max(_min_speed, current_speed - 0.5)
        self.simulation_interval = int(self.simulation_base_interval / new_speed)
        self.simulation_timer.setInterval(self.simulation_interval)
        self.view.dashboard.update_simulation_speed(f"{new_speed:.1f}x")
