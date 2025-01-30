"""Main controller module for the BRMS application."""

import datetime

from PySide6.QtCore import QTimer, Signal

from brms import DEBUG_MODE
from brms.controllers.bank_controller import BankController
from brms.controllers.base import BRMSController
from brms.controllers.inspector_controller import InspectorController
from brms.controllers.yield_curve_controller import YieldCurveController
from brms.data import DEFAULT_DATA_FOLDER
from brms.data.default import SIMULATION_START_DATE
from brms.models.scenario import Scenario
from brms.models.simulation import Simulation as SimulationModel
from brms.views.main_window import MainWindow


class MainController(BRMSController):
    """Main controller class for the Simulation."""

    simulation_initiated = Signal(SimulationModel)
    scenario_changed = Signal(Scenario)

    def __init__(self, model: SimulationModel, view: MainWindow) -> None:
        """Initialize the MainController."""
        super().__init__()
        self.simulation: SimulationModel = model
        self.view: MainWindow = view
        # Initialize the timer
        self.simulation_base_interval = 500
        self.simulation_interval = self.simulation_base_interval
        self.simulation_timer = QTimer()
        self.simulation_timer.setInterval(self.simulation_interval)
        # Sub controllers
        self.inspector_ctrl = InspectorController(inspector_widget=self.view.inspector_widget)
        self.bank_ctrl = BankController(
            bank=self.simulation.bank,
            banking_book_view=self.view.banking_book_widget,
            trading_book_view=self.view.trading_book_widget,
            inspector_ctrl=self.inspector_ctrl,
            statement_view=self.view.statement_viewer_widget,
        )
        self.yield_curve_ctrl = YieldCurveController(view=self.view.yield_curve_widget)
        # Connect signals
        self.connect_signals()
        if DEBUG_MODE:
            self.connect_signals_for_debugging()
        # Initial tasks
        self.bank_ctrl.update_statement()
        QTimer.singleShot(100, self.init)

    def connect_signals(self) -> None:
        """Connect signals from the view to the controller's slots."""
        self.simulation_timer.timeout.connect(self.on_next_scenario)
        self.view.next_action.triggered.connect(self.on_next_scenario)
        self.view.start_action.triggered.connect(self.on_start_action)
        self.view.pause_action.triggered.connect(self.on_pause_action)
        self.view.stop_action.triggered.connect(self.on_stop_action)
        self.view.speed_up_action.triggered.connect(self.on_speed_up_action)
        self.view.speed_down_action.triggered.connect(self.on_speed_down_action)
        self.view.exit_signal.connect(self.on_exit)
        self.scenario_changed.connect(self.on_scenario_changed)
        self.simulation_initiated.connect(self.on_simulation_initiated)

        self.bank_ctrl.bank_financials_updated.connect(self.view.dashboard.update_bank_financials)
        self.bank_ctrl.transaction_processed.connect(self.view.transaction_history_widget.add_transaction)

    def connect_signals_for_debugging(self) -> None:
        """Connect signals only used for debugging."""
        debug_panel = self.view.debug_panel
        debug_panel.btn_init.clicked.connect(self._test_init)
        debug_panel.btn_buy_htm_security.clicked.connect(self._test_buy_htm_security)

    def init(self) -> None:
        """Initialize the simulation and set the starting scenario.

        These should be init actions on a fresh stimulation start.
        """
        # 0. Reset simulation
        self.simulation.reset()
        # 1. Scenario manager loads data
        self.simulation.scenario_manager.load_data("csv", DEFAULT_DATA_FOLDER)
        # 2. Simulation sets the starting scenario (date)
        self.simulation.set_scenario(SIMULATION_START_DATE)
        # 3. Initialize sub controllers and load initial data if necessary
        self.yield_curve_ctrl.init(self.simulation.scenario_manager)
        self.bank_ctrl.init(self.simulation.scenario_manager)
        # 4. Emit signal about Scenario changes
        self.scenario_changed.emit(self.simulation.current_scenario)
        self.simulation_initiated.emit(self.simulation)
        # misc
        self.view.transaction_history_widget.set_end_date(self.simulation.current_scenario.date)
        self.view.transaction_history_widget.set_start_date(self.simulation.current_scenario.date)

    def on_exit(self) -> None:
        """Handle the exit signal from the view."""
        # Perform any cleanup or save operations here
        self.view.close()

    def on_simulation_initiated(self, simulation: SimulationModel) -> None:
        self.simulation.start_date = self.simulation.current_scenario.date
        self.view.dashboard.update_simulation_progress(0)
        self.view.dashboard.update_simulation_date(simulation.current_scenario.date)
        self.view.dashboard.update_simulation_start_date(self.simulation.start_date)
        self.view.dashboard.update_simulation_end_date(self.simulation.end_date)
        self.update_dashboard()

    def update_dashboard(self) -> None:
        self.view.dashboard.update_assets_plot(
            start=self.simulation.start_date,
            end=self.simulation.end_date,
            dates=list(self.bank_ctrl.total_assets_history.keys()),
            assets_values=list(self.bank_ctrl.total_assets_history.values()),
        )
        self.view.dashboard.update_liabilities_plot(
            start=self.simulation.start_date,
            end=self.simulation.end_date,
            dates=list(self.bank_ctrl.total_liabilities_history.keys()),
            liabilities_values=list(self.bank_ctrl.total_liabilities_history.values()),
        )
        self.view.dashboard.update_equity_plot(
            start=self.simulation.start_date,
            end=self.simulation.end_date,
            dates=list(self.bank_ctrl.total_equity_history.keys()),
            equity_values=list(self.bank_ctrl.total_equity_history.values()),
        )

    def on_next_scenario(self) -> None:
        self.simulation.scenario_manager.current_date += datetime.timedelta(days=1)
        # Dates in simulation scenarios can have gaps due to non-business days
        date = self.simulation.scenario_manager.current_date
        while not self.simulation.scenario_manager.has_scenario(date):
            # Some transactions (e.g., mortgage payments) do not require a scenario (w/ term structure, etc.)
            for tx in self.simulation.bank_engine.generate_transactions(date):
                self.bank_ctrl.process_transaction(tx)
            date += datetime.timedelta(days=1)
            if date > self.simulation.end_date:
                self.on_pause_action()  # TODO: on stop
                return
        # Advanced to a date with scenario
        self.simulation.set_scenario(date)
        self.simulation.scenario_manager.current_date = date
        for tx in self.simulation.bank_engine.generate_transactions(date):
            self.bank_ctrl.process_transaction(tx)
        self.scenario_changed.emit(self.simulation.current_scenario)
        # Update statistics
        self.view.dashboard.update_simulation_date(date)
        start_date = self.simulation.start_date
        end_date = self.simulation.end_date
        progress = (date - start_date) / (end_date - start_date) * 100
        self.view.dashboard.update_simulation_progress(int(progress))
        self.update_dashboard()
        self.view.transaction_history_widget.set_end_date(self.simulation.current_scenario.date)

    def on_scenario_changed(self, scenario: Scenario) -> None:
        """Handle changes to the scenario.

        These should be repeated actions on each scenario change
        """
        self.view.statusBar().showMessage(f"Current date: {scenario.date}")
        # Pass the new scenario to controllers orderly
        self.yield_curve_ctrl.set_scenario(scenario)
        self.bank_ctrl.update_statement(scenario.date)

    def on_start_action(self):
        self.view.next_action.setDisabled(True)
        self.view.start_action.setDisabled(True)
        self.view.pause_action.setEnabled(True)
        self.view.stop_action.setEnabled(True)
        self.simulation_timer.start()

    def on_pause_action(self):
        self.view.next_action.setEnabled(True)
        self.view.start_action.setEnabled(True)
        self.view.pause_action.setDisabled(True)
        self.view.stop_action.setDisabled(True)
        self.simulation_timer.stop()

    def on_stop_action(self):
        self.view.next_action.setDisabled(True)
        self.view.start_action.setDisabled(True)
        self.view.pause_action.setDisabled(True)
        self.view.stop_action.setDisabled(True)
        self.simulation_timer.stop()

    def on_speed_up_action(self):
        # Increase speed by 0.5x
        current_speed = self.simulation_base_interval / self.simulation_timer.interval()
        current_speed = round(current_speed, 1)
        # Ensure the speed does not exceed 5.0x
        new_speed = 0.5 if current_speed == 0.1 else min(5.0, current_speed + 0.5)
        self.simulation_interval = int(self.simulation_base_interval / new_speed)
        self.simulation_timer.setInterval(self.simulation_interval)
        self.view.dashboard.update_simulation_speed(f"{new_speed:.1f}x")

    def on_speed_down_action(self):
        # Decrease speed by 0.5x
        current_speed = self.simulation_base_interval / self.simulation_timer.interval()
        current_speed = round(current_speed, 1)
        new_speed = max(0.1, current_speed - 0.5)  # Ensure the speed does not go below 0.1x
        self.simulation_interval = int(self.simulation_base_interval / new_speed)
        self.simulation_timer.setInterval(self.simulation_interval)
        self.view.dashboard.update_simulation_speed(f"{new_speed:.1f}x")

    # ====================================================================
    # Testing
    # ====================================================================

    def _test_init(self) -> None:
        self.init()

    def _test_buy_htm_security(self) -> None:
        import QuantLib as ql

        from brms.instruments.base import BookType, CreditRating, Issuer, IssuerType
        from brms.instruments.fixed_rate_bond import FixedRateBond
        from brms.models.transaction import TransactionFactory, TransactionType

        face_value = 5000.0
        coupon_rate = 0.05
        issue_date = ql.Date(1, 1, 2020)
        maturity_date = ql.Date(1, 1, 2030)
        bond = FixedRateBond(
            face_value=face_value,
            coupon_rate=coupon_rate,
            issue_date=issue_date,
            maturity_date=maturity_date,
            book_type=BookType.BANKING_BOOK,
            credit_rating=CreditRating.AA_MINUS,
            issuer=Issuer(
                name="Asian Development Bank",
                issuer_type=IssuerType.MDB,
                credit_rating=CreditRating.AA,
            ),
        )
        bond.value = face_value
        tx = TransactionFactory.create_transaction(
            bank=self.simulation.bank,
            transaction_type=TransactionType.SECURITY_PURCHASE_HTM,
            instrument=bond,
            transaction_date=issue_date,
        )
        self.bank_ctrl.process_transaction(tx)
        self.bank_ctrl.update_statement()
