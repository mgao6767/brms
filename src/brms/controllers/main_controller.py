"""Main controller module for the BRMS application."""

from brms.controllers.bank_controller import BankController
from brms.controllers.base import BRMSController
from brms.controllers.inspector_controller import InspectorController
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
        )
        # Connect signals
        self.connect_signals()

    def connect_signals(self) -> None:
        """Connect signals from the view to the controller's slots."""
        self.view.exit_signal.connect(self.handle_exit)

    def handle_exit(self) -> None:
        """Handle the exit signal from the view."""
        # Perform any cleanup or save operations here
        self.view.close()
