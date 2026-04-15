"""Main controller module for the BRMS application."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QFileDialog, QTreeView

from brms.app import clipboard
from brms.app.controllers.bank_controller import BankController
from brms.app.controllers.base import BRMSController
from brms.app.controllers.dashboard_controller import DashboardController
from brms.app.controllers.inspector_controller import InspectorController
from brms.app.controllers.interest_rate_risk_controller import InterestRateRiskController
from brms.app.controllers.statement_controller import StatementController
from brms.app.controllers.transaction_history_controller import TransactionHistoryController
from brms.app.controllers.yield_curve_controller import YieldCurveController
from brms.core.events import ShowTransactionsRequested
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
        self.inspector_ctrl.connect_signals()
        self.dashboard_ctrl: DashboardController
        self.transaction_history_ctrl: TransactionHistoryController
        self.statement_ctrl: StatementController
        self.bank_ctrl: BankController
        self.yield_curve_ctrl: YieldCurveController
        self.interest_rate_risk_ctrl: InterestRateRiskController

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
        self.view.speed_combo.currentTextChanged.connect(self._on_speed_changed)
        self.view.open_action.triggered.connect(self.on_open_action)
        self.view.copy_value_action.triggered.connect(self._on_copy_value)
        self.view.copy_row_action.triggered.connect(self._on_copy_row)
        self.view.copy_details_action.triggered.connect(self._on_copy_details)
        self.view.exit_signal.connect(self.on_exit)
        self.view.tab_widget.currentChanged.connect(self._on_tab_changed)
        self.view.dock_statement_viewer.visibilityChanged.connect(self._on_statement_dock_visible)

    def load_simulation(self, services: CoreServices) -> None:
        """(Re)initialize all sub-controllers and views for a loaded simulation."""
        # Clear stale data via existing controllers (skip on first load)
        if hasattr(self, "transaction_history_ctrl"):
            self.transaction_history_ctrl.reset()
            self.statement_ctrl.reset()
            self.bank_ctrl.reset()
            self.yield_curve_ctrl.reset()

        self.services = services
        self.on_pause_action()
        eb = services.event_bus
        view = self.view

        start_date = services.simulation_service.start_date
        end_date = services.simulation_service.end_date

        self.dashboard_ctrl = DashboardController(
            view=view.dashboard,
            event_bus=eb,
            reporting_service=services.reporting_service,
            ledger=services.bank.ledger,
            metric_store=services.metric_store,
            start_date=start_date,
            end_date=end_date,
        )
        self.inspector_ctrl.bind_services(
            bank=services.bank,
            journal=services.bank.ledger.journal,
        )
        self.transaction_history_ctrl = TransactionHistoryController(
            view=view.transaction_history_widget,
            event_bus=eb,
            transaction_log=services.transaction_log,
            inspector_ctrl=self.inspector_ctrl,
            start_date=start_date,
            end_date=end_date,
        )
        self.statement_ctrl = StatementController(
            view=view.statement_viewer_widget,
            event_bus=eb,
            reporting_service=services.reporting_service,
            ledger=services.bank.ledger,
        )
        # Build initial valuations from the seeded ValuationStore
        from brms.core.enums import ValuationType

        initial_valuations: dict = {}
        if start_date is not None:
            initial_valuations = {
                **services.valuation_store.snapshot(start_date, ValuationType.CARRYING_VALUE),
                **services.valuation_store.snapshot(start_date, ValuationType.FAIR_VALUE),
            }

        self.bank_ctrl = BankController(
            bank=services.bank,
            event_bus=eb,
            combined_book_view=view.combined_book_widget,
            inspector_ctrl=self.inspector_ctrl,
            initial_valuations=initial_valuations,
        )
        self.yield_curve_ctrl = YieldCurveController(
            view=view.yield_curve_widget,
            event_bus=eb,
            market_data=services.market_data,
        )
        self.interest_rate_risk_ctrl = InterestRateRiskController(
            view=view.interest_rate_risk_widget,
            event_bus=eb,
            bank=services.bank,
            valuation_store=services.valuation_store,
        )

        # Subscribe to events
        eb.subscribe(ShowTransactionsRequested, self._on_show_transactions_requested)

        # Populate views from current state
        self.statement_ctrl.refresh()
        self.transaction_history_ctrl.load_initial()
        self.dashboard_ctrl.init()
        self.yield_curve_ctrl.init()
        self.interest_rate_risk_ctrl.init(start_date)

        # Advance first day so dashboard metrics and plots are populated
        self.on_advance()
        # Flush deferred updates — window may not be visible yet on first load
        self.dashboard_ctrl.on_visible()

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

    def _on_show_transactions_requested(self, event: ShowTransactionsRequested) -> None:
        """Switch to Transaction History tab and filter by instrument."""
        tx_tab_index = self.view.tab_widget.indexOf(self.view.transaction_history_widget)
        self.view.tab_widget.setCurrentIndex(tx_tab_index)
        self.transaction_history_ctrl.filter_by_instrument(event.instrument_id)

    def _on_tab_changed(self, index: int) -> None:
        """Flush deferred updates when a tab becomes visible."""
        if self.view.tab_widget.widget(index) is self.view.dashboard:
            self.dashboard_ctrl.on_visible()
        if self.view.tab_widget.widget(index) is self.view.interest_rate_risk_widget:
            self.interest_rate_risk_ctrl.on_visible()

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

    def _on_speed_changed(self, text: str) -> None:
        """Handle speed dropdown change (e.g. '2x' → 2.0)."""
        multiplier = float(text.rstrip("x"))
        self.simulation_interval = int(self.simulation_base_interval / multiplier)
        self.simulation_timer.setInterval(self.simulation_interval)

    def _focused_tree(self) -> QTreeView | None:
        """Return the currently focused QTreeView, or None."""
        widget = QApplication.focusWidget()
        if isinstance(widget, QTreeView):
            return widget
        return None

    def _on_copy_value(self) -> None:
        """Copy the selected cell's value from the focused tree."""
        if tree := self._focused_tree():
            clipboard.copy_tree_value(tree)

    def _on_copy_row(self) -> None:
        """Copy the selected row from the focused tree."""
        if tree := self._focused_tree():
            clipboard.copy_tree_row(tree)

    def _on_copy_details(self) -> None:
        """Copy inspector details to clipboard."""
        self.inspector_ctrl.copy_details()
