"""Main controller module for the BRMS application."""

from brms import DEBUG_MODE
from brms.controllers.bank_controller import BankController
from brms.controllers.base import BRMSController
from brms.controllers.inspector_controller import InspectorController
from brms.controllers.yield_curve_controller import YieldCurveController
from brms.models.simulation import Simulation as SimulationModel
from brms.views.main_window import MainWindow


class MainController(BRMSController):
    """Main controller class for handling the interaction between the model and view."""

    def __init__(self, model: SimulationModel, view: MainWindow) -> None:
        """Initialize the MainController."""
        self.simulation: SimulationModel = model
        self.view: MainWindow = view
        # Sub controllers
        self.inspector_ctrl = InspectorController(inspector_widget=self.view.inspector_widget)
        self.bank_ctrl = BankController(
            bank=self.simulation.bank,
            banking_book_view=self.view.banking_book_widget,
            trading_book_view=self.view.trading_book_widget,
            inspector_ctrl=self.inspector_ctrl,
            statement_view=self.view.statement_viewer_widget,
        )
        self.yield_curve_ctrl = YieldCurveController(
            model=self.simulation.scenario_manager.yield_curve,  # Yield curve model belongs to the scenario manager
            view=self.view.yield_curve_widget,
        )
        # Connect signals
        self.connect_signals()
        # Initial tasks
        self.bank_ctrl.update_statement()

    def connect_signals(self) -> None:
        """Connect signals from the view to the controller's slots."""
        self.view.exit_signal.connect(self.handle_exit)

        if DEBUG_MODE:
            self.connect_signals_for_debugging()

    def connect_signals_for_debugging(self) -> None:
        """Connect signals only used for debugging."""
        debug_panel = self.view.debug_panel
        debug_panel.btn_init_bank.clicked.connect(self.bank_ctrl._test_init)
        debug_panel.btn_buy_htm_security.clicked.connect(self.bank_ctrl._test_buy_htm_security)

    def handle_exit(self) -> None:
        """Handle the exit signal from the view."""
        # Perform any cleanup or save operations here
        self.view.close()
