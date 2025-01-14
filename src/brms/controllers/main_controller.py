"""Main controller module for the BRMS application."""

from brms.models.simulation import Simulation as SimulationModel
from brms.views.main_window import MainWindow


class MainController:
    """Main controller class for handling the interaction between the model and view."""

    def __init__(self, model: SimulationModel, view: MainWindow) -> None:
        """Initialize the MainController."""
        self.scenario: SimulationModel = model
        self.view: MainWindow = view
