"""Main controller module for the BRMS application."""

from brms.models.simulation import Simulation as SimulationModel
from brms.views.main_window import MainWindow


class MainController:
    """Main controller class for handling the interaction between the model and view."""

    def __init__(self, model: SimulationModel, view: MainWindow) -> None:
        """Initialize the MainController."""
        self.scenario: SimulationModel = model
        self.view: MainWindow = view
        self.connect_signals()

    def connect_signals(self) -> None:
        """Connect signals from the view to the controller's slots."""
        self.view.exit_signal.connect(self.handle_exit)

    def handle_exit(self) -> None:
        """Handle the exit signal from the view."""
        # Perform any cleanup or save operations here
        self.view.close()
