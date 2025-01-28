"""Main module for the BRMS application."""

import sys

from PySide6.QtWidgets import QApplication

from brms import DEBUG_MODE
from brms.controllers.main_controller import MainController
from brms.models.simulation import Simulation as SimulationModel
from brms.views.main_window import MainWindow


class App(QApplication):
    """BRMS application."""

    def __init__(self, sys_argv: list[str]) -> None:
        """Initialize the BRMS application."""
        super().__init__(sys_argv)
        font = self.font()
        font.setFamily("Monospace")
        self.setFont(font)
        self.view = MainWindow()
        self.model = SimulationModel()
        self.controller = MainController(self.model, self.view)
        self.view.show()
        if DEBUG_MODE:
            self.view.debug_panel.show()


def main() -> None:
    """Run the main entry point for the BRMS application."""
    app = App(sys.argv)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
