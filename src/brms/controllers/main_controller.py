"""Main controller module for the BRMS application."""

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

    scenario_changed = Signal(Scenario)

    def __init__(self, model: SimulationModel, view: MainWindow) -> None:
        """Initialize the MainController."""
        super().__init__()
        self.simulation: SimulationModel = model
        self.view: MainWindow = view
        # Initialize the timer
        self.simulation_interval = 500
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

    def on_exit(self) -> None:
        """Handle the exit signal from the view."""
        # Perform any cleanup or save operations here
        self.view.close()

    def on_next_scenario(self) -> None:
        try:
            date = self.simulation.scenario_manager.get_date_of_next_scenario()
        except ValueError:  # "Current scenario is not set." when data not loaded
            self.on_pause_action()
            return
        if date is None:  # no more scenarios
            self.on_pause_action()
            return
        self.simulation.set_scenario(date)
        for tx in self.simulation.bank_engine.generate_transactions(date):
            self.bank_ctrl.process_transaction(tx)
        self.scenario_changed.emit(self.simulation.current_scenario)

    def on_scenario_changed(self, scenario: Scenario) -> None:
        """Handle changes to the scenario.

        These should be repeated actions on each scenario change
        """
        self.view.statusBar().showMessage(f"Current date: {scenario.date}")
        # Pass the new scenario to controllers orderly
        self.yield_curve_ctrl.set_scenario(scenario)
        # TODO: transactions
        self.bank_ctrl.update_statement()

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
        # min interval 100ms or 0.1s
        self.simulation_interval = max(100, self.simulation_timer.interval() - 100)
        self.simulation_timer.setInterval(self.simulation_interval)

    def on_speed_down_action(self):
        # max interval 2000ms or 2s
        self.simulation_interval = min(2000, self.simulation_timer.interval() + 100)
        self.simulation_timer.setInterval(self.simulation_interval)

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
