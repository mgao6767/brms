"""Main window class for the BRMS application."""

from PySide6.QtCore import Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QApplication, QMainWindow, QMenuBar, QStatusBar, QToolBar

from brms import __version__


class MainWindow(QMainWindow):
    """Main window class for the BRMS application."""

    exit_signal = Signal()

    def __init__(self) -> None:
        """Initialize the main window."""
        super().__init__()
        self.read_settings()
        self.init_ui()
        self.connect_signals()
        # Actions
        self.exit_action: QAction

    def init_ui(self) -> None:
        """Initialize the user interface."""
        self.set_window_properties()
        self.create_actions()
        self.create_menubar()
        self.create_toolbar()
        self.create_statusbar()
        self.center_window()

    def read_settings(self) -> None:
        """Read and set the default window settings."""
        screen_geometry = QApplication.primaryScreen().availableGeometry()
        self.window_width = min(1920, screen_geometry.width())
        self.window_height = min(1080, screen_geometry.height())

    def set_window_properties(self) -> None:
        """Set the properties of the main window."""
        self.setWindowTitle(f"BRMS - Bank Risk Management Simulation v{__version__}")
        self.setGeometry(100, 100, self.window_width, self.window_height)
        self.setMinimumSize(800, 600)

    def center_window(self) -> None:
        """Center the main window on the screen."""
        screen_geometry = QApplication.primaryScreen().availableGeometry()
        x = (screen_geometry.width() - self.window_width) // 2
        y = (screen_geometry.height() - self.window_height) // 2
        self.move(x, y)

    def create_actions(self) -> None:
        """Create actions for the main window."""
        self.exit_action = QAction("Exit", self)

    def create_toolbar(self) -> None:
        """Create the toolbar for the main window."""
        toolbar = QToolBar("Main Toolbar")
        self.addToolBar(toolbar)
        # Add actions to the toolbar

    def create_menubar(self) -> None:
        """Create the menubar for the main window."""
        menubar = QMenuBar(self)
        self.setMenuBar(menubar)
        # Add menus to the menubar
        file_menu = menubar.addMenu("File")
        # Add actions to the menus
        file_menu.addAction(self.exit_action)

    def create_statusbar(self) -> None:
        """Create the status bar for the main window."""
        statusbar = QStatusBar(self)
        self.setStatusBar(statusbar)
        statusbar.showMessage("Ready")

    def connect_signals(self) -> None:
        """Connect signals to their respective slots."""
        self.exit_action.triggered.connect(self.on_exit)

    def on_exit(self) -> None:
        """Handle the exit action.

        Emit the exit signal and delegate the closing tasks to the controller.
        """
        self.exit_signal.emit()
