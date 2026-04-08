"""BRMS Qt application."""

import sys
from dataclasses import fields

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from brms import DEBUG_MODE
from brms.app.controllers.main_controller import MainController
from brms.app.views.main_window import MainWindow
from brms.core.services import CoreServices
from brms.resources import icons  # noqa: F401


class App(QApplication):
    """BRMS application."""

    def __init__(self, sys_argv: list[str], services: CoreServices) -> None:
        """Initialize the BRMS application."""
        super().__init__(sys_argv)

        # On Windows, set the app user model ID so the taskbar shows our icon.
        if sys.platform == "win32":
            import ctypes

            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("brms.brms")

        self.setWindowIcon(QIcon(":/icons/icon.png"))

        font = self.font()
        font.setFamily("Monospace")
        self.setFont(font)

        self.view = MainWindow()
        # Bridge: MainController still expects dict until Task 7
        services_dict = {f.name: getattr(services, f.name) for f in fields(services)}
        self.controller = MainController(self.view, core_services=services_dict)
        self.view.show()
        if DEBUG_MODE:
            self.view.debug_panel.show()
