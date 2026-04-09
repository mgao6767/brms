"""Main controller module for the BRMS application."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QFileDialog

from brms.app.controllers.bank_controller import BankController
from brms.app.controllers.base import BRMSController
from brms.app.controllers.dashboard_controller import DashboardController
from brms.app.controllers.inspector_controller import InspectorController
from brms.app.controllers.statement_controller import StatementController
from brms.app.controllers.transaction_history_controller import TransactionHistoryController
from brms.app.controllers.yield_curve_controller import YieldCurveController
from brms.core.services import build_core_services

if TYPE_CHECKING:
    from brms.app.views.main_window import MainWindow
    from brms.core.services import CoreServices

logger = logging.getLogger(__name__)


class MainController(BRMSController):
    """Thin orchestrator: owns sub-controllers and simulation timer."""

    def __init__(self, view: MainWindow, services: CoreServices) -> None:
        """Initialize the MainController."""
        super().__init__()
        self.view = view

        # Sub-controllers (created once, rebound on load)
        self.inspector_ctrl = InspectorController(inspector_widget=view.inspector_widget)
        self.dashboard_ctrl: DashboardController
        self.transaction_history_ctrl: TransactionHistoryController
        self.statement_ctrl: StatementController
        self.bank_ctrl: BankController
        self.yield_curve_ctrl: YieldCurveController

        # Simulation timer
        self.simulation_base_interval = 500
        self.simulation_interval = self.simulation_base_interval
        self.simulation_timer = QTimer()
        self.simulation_timer.setInterval(self.simulation_interval)

        self._connect_toolbar_signals()
        self.load_simulation(services)

    def _connect_toolbar_signals(self) -> None:
        """Connect toolbar and menu actions (done once, not per simulation load)."""
        self.simulation_timer.timeout.connect(self.on_advance)
        self.view.next_action.triggered.connect(self.on_advance)
        self.view.start_action.triggered.connect(self.on_start_action)
        self.view.pause_action.triggered.connect(self.on_pause_action)
        self.view.stop_action.triggered.connect(self.on_stop_action)
        self.view.speed_up_action.triggered.connect(self.on_speed_up_action)
        self.view.speed_down_action.triggered.connect(self.on_speed_down_action)
        self.view.open_action.triggered.connect(self.on_open_action)
        self.view.exit_signal.connect(self.on_exit)
        self.view.tab_widget.currentChanged.connect(self._on_tab_changed)
        self.view.dock_statement_viewer.visibilityChanged.connect(self._on_statement_dock_visible)

    def load_simulation(self, services: CoreServices) -> None:
        """(Re)initialize all sub-controllers and views for a loaded simulation."""
        # Clear stale data via existing controllers (skip on first load)
        if hasattr(self, "transaction_history_ctrl"):
            self.transaction_history_ctrl.reset()
            self.bank_ctrl.reset()
            self.yield_curve_ctrl.reset()

        self.services = services
        self.on_pause_action()
        eb = services.event_bus
        view = self.view

        dates = services.market_data.available_dates()
        start_date = dates[0] if dates else None
        end_date = dates[-1] if dates else None

        self.dashboard_ctrl = DashboardController(
            view=view.dashboard,
            event_bus=eb,
            reporting_service=services.reporting_service,
            ledger=services.bank.ledger,
            start_date=start_date,
            end_date=end_date,
        )
        self.transaction_history_ctrl = TransactionHistoryController(
            view=view.transaction_history_widget,
            event_bus=eb,
            transaction_log=services.transaction_log,
            journal=services.bank.ledger.journal,
            start_date=start_date,
            end_date=end_date,
        )
        self.statement_ctrl = StatementController(
            view=view.statement_viewer_widget,
            event_bus=eb,
            reporting_service=services.reporting_service,
            ledger=services.bank.ledger,
        )
        self.bank_ctrl = BankController(
            bank=services.bank,
            event_bus=eb,
            banking_book_view=view.banking_book_widget,
            trading_book_view=view.trading_book_widget,
            inspector_ctrl=self.inspector_ctrl,
        )
        self.yield_curve_ctrl = YieldCurveController(
            view=view.yield_curve_widget,
            event_bus=eb,
            market_data=services.market_data,
        )

        # Populate views from current state
        self.statement_ctrl.refresh()
        self.transaction_history_ctrl.load_initial()
        self.dashboard_ctrl.init()
        self.yield_curve_ctrl.init()

        # Advance first day so dashboard metrics and plots are populated
        self.on_advance()

    def on_open_action(self) -> None:
        """Open a simulation zip file and reload."""
        file_path, _ = QFileDialog.getOpenFileName(
            self.view,
            caption="Open Simulation",
            filter="Simulation Files (*.zip);;All Files (*)",
        )
        if not file_path:
            return
        services = build_core_services(simulation_zip=Path(file_path))
        self.load_simulation(services)

    def _on_tab_changed(self, index: int) -> None:
        """Flush deferred updates when a tab becomes visible."""
        if self.view.tab_widget.widget(index) is self.view.dashboard:
            self.dashboard_ctrl.on_visible()

    def _on_statement_dock_visible(self, visible: bool) -> None:  # noqa: FBT001
        """Flush deferred statement render when dock becomes visible."""
        if visible:
            self.statement_ctrl.on_visible()

    def on_exit(self) -> None:
        """Handle the exit signal from the view."""
        self.view.close()

    def on_advance(self) -> None:
        """Advance simulation by one step."""
        try:
            self.services.simulation_service.advance()
        except IndexError:
            logger.info("No more dates; pausing.")
            self.on_pause_action()

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
        new_speed = 0.5 if current_speed == 0.1 else min(5.0, current_speed + 0.5)  # noqa: PLR2004
        self.simulation_interval = int(self.simulation_base_interval / new_speed)
        self.simulation_timer.setInterval(self.simulation_interval)
        self.dashboard_ctrl.update_speed(f"{new_speed:.1f}x")

    def on_speed_down_action(self) -> None:
        """Decrease the simulation speed by 0.5x."""
        current_speed = self.simulation_base_interval / self.simulation_timer.interval()
        current_speed = round(current_speed, 1)
        new_speed = max(0.1, current_speed - 0.5)
        self.simulation_interval = int(self.simulation_base_interval / new_speed)
        self.simulation_timer.setInterval(self.simulation_interval)
        self.dashboard_ctrl.update_speed(f"{new_speed:.1f}x")
