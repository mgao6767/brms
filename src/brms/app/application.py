"""BRMS Qt application."""

import sys

import qtawesome as qta
from PySide6.QtGui import QFont, QIcon
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
        font.setStyleHint(QFont.StyleHint.SansSerif)
        font.setPointSize(8)
        self.setFont(font)

        qta.set_defaults(color="#A8B3C2")

        self.view = MainWindow()
        self.controller = MainController(self.view, services=services)
        self.view.show()
        if DEBUG_MODE:
            self.view.debug_panel.show()
