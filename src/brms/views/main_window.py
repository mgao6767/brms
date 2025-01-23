"""Main window class for the BRMS application."""

import qtawesome as qta
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QDockWidget,
    QMainWindow,
    QMenuBar,
    QStatusBar,
    QTabWidget,
    QToolBar,
    QWidget,
)

from brms import __about__, __github__, __version__
from brms.resources import icons  # noqa: F401
from brms.views.bank_book_widget import (
    BRMSBankingBookWidget,
    BRMSTradingBookWidget,
)
from brms.views.dock_widget import BRMSDockWidget
from brms.views.statement_viewer_widget import BRMSStatementViewer
from brms.views.inspector_widget import BRMSInspectorWidget


class MainWindow(QMainWindow):
    """Main window class for the BRMS application."""

    exit_signal = Signal()

    def __init__(self) -> None:
        """Initialize the main window."""
        super().__init__()
        self.read_settings()
        # UI components
        self.inspector_widget: BRMSInspectorWidget
        self.banking_book_widget: BRMSBankingBookWidget
        self.trading_book_widget: BRMSTradingBookWidget
        self.statement_viewer_widget: BRMSStatementViewer
        self._dock_widgets: list[BRMSDockWidget] = []
        self.init_ui()
        self.connect_signals()
        # Actions
        self.new_action: QAction
        self.open_action: QAction
        self.save_action: QAction
        self.exit_action: QAction
        self.next_action: QAction
        self.start_action: QAction
        self.pause_action: QAction
        self.stop_action: QAction
        self.about_action: QAction
        self.github_action: QAction

    def init_ui(self) -> None:
        """Initialize the user interface."""
        self.set_window_properties()
        self.create_actions()
        self.create_menubar()
        self.create_toolbar()
        self.create_statusbar()
        self.create_central_widget()
        self.create_dock_widgets()

    def create_central_widget(self) -> None:
        """Create the central widget."""
        tab_widget = QTabWidget(self)
        self.banking_book_widget = BRMSBankingBookWidget()
        self.trading_book_widget = BRMSTradingBookWidget()
        # tab_widget.addTab(self.statement_viewer_widget, "Dashboard")
        tab_widget.addTab(self.banking_book_widget, "Banking Book")
        tab_widget.addTab(self.trading_book_widget, "Trading Book")
        self.setCentralWidget(tab_widget)

    def read_settings(self) -> None:
        """Read and set the default window settings."""
        self.setWindowIcon(QIcon(":/icons/icon.png"))
        screen_geometry = QApplication.primaryScreen().availableGeometry()
        self.window_width = min(1920, screen_geometry.width())
        self.window_height = min(1080, screen_geometry.height())

    def set_window_properties(self) -> None:
        """Set the properties of the main window."""
        self.setWindowTitle(f"BRMS - Bank Risk Management Simulation v{__version__}")
        self.resize(self.window_width, self.window_height)
        self.setMinimumSize(1024, 768)

    def center_window(self) -> None:
        """Center the main window on the screen."""
        screen_geometry = QApplication.primaryScreen().availableGeometry()
        x = (screen_geometry.width() - self.window_width) // 2
        y = (screen_geometry.height() - self.window_height) // 2
        self.move(x, y)

    def create_actions(self) -> None:
        """Create actions for the main window."""
        self.new_action = QAction("New", self)
        self.open_action = QAction("Open", self)
        self.save_action = QAction("Save", self)
        self.exit_action = QAction(qta.icon("mdi6.exit-run"), "Exit", self)
        self.exit_action.setShortcut("Ctrl+Q")

        self.next_action = QAction(qta.icon("mdi6.skip-next"), "Next", self)
        self.start_action = QAction(qta.icon("mdi6.play"), "Start", self)
        self.pause_action = QAction(qta.icon("mdi6.pause"), "Pause", self)
        self.stop_action = QAction(qta.icon("mdi6.stop"), "Stop", self)

        self.about_action = QAction("About", self)
        self.github_action = QAction(qta.icon("mdi6.github"), "GitHub", self)

    def create_toolbar(self) -> None:
        """Create the toolbar for the main window."""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.addToolBar(toolbar)
        # Add actions to the toolbar
        toolbar.addAction(self.next_action)
        toolbar.addAction(self.start_action)
        toolbar.addAction(self.pause_action)
        toolbar.addAction(self.stop_action)

    def create_menubar(self) -> None:
        """Create the menubar for the main window."""
        menubar = QMenuBar(self)
        self.setMenuBar(menubar)
        # Add menus to the menubar
        file_menu = menubar.addMenu("File")
        edit_menu = menubar.addMenu("Edit")
        view_menu = menubar.addMenu("View")
        simulation_menu = menubar.addMenu("Simulation")
        help_menu = menubar.addMenu("Help")
        # Add actions to the menus
        # File menu
        file_menu.addAction(self.new_action)
        file_menu.addAction(self.open_action)
        file_menu.addAction(self.save_action)
        file_menu.addSeparator()
        file_menu.addAction(self.exit_action)
        # Simulation menu
        simulation_menu.addAction(self.next_action)
        simulation_menu.addAction(self.start_action)
        simulation_menu.addAction(self.pause_action)
        simulation_menu.addAction(self.stop_action)
        # Help menu
        help_menu.addAction(self.about_action)
        help_menu.addAction(self.github_action)

    def create_statusbar(self) -> None:
        """Create the status bar for the main window."""
        statusbar = QStatusBar(self)
        self.setStatusBar(statusbar)
        statusbar.showMessage("Ready")

    def create_dock_widgets(self) -> None:
        """Create and dock the inspector widget."""
        # Inspector
        dock_inspector = BRMSDockWidget("Inspector", self)
        self.inspector_widget = BRMSInspectorWidget(["Property", "Value"], dock_inspector)
        dock_inspector.setWidget(self.inspector_widget)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock_inspector)
        self._dock_widgets.append(dock_inspector)
        # Economic indicator
        dock_econ_indicator = BRMSDockWidget("Economic Indicators", self)
        econ_indicator_widget = QTabWidget()
        econ_indicator_widget.addTab(QWidget(), "Yield Curve")
        econ_indicator_widget.addTab(QWidget(), "Stock Market")
        dock_econ_indicator.setWidget(econ_indicator_widget)  # TODO: placeholder widget
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, dock_econ_indicator)
        self._dock_widgets.append(dock_econ_indicator)
        # Statements viewer
        dock_statement_viewer = BRMSDockWidget("Financial Statements", self)
        dock_statement_viewer.setMinimumWidth(400)
        self.statement_viewer_widget = BRMSStatementViewer()
        dock_statement_viewer.setWidget(self.statement_viewer_widget)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, dock_statement_viewer)
        self._dock_widgets.append(dock_statement_viewer)
        # Resize statement viewer when user's screen size is large enough
        screen_geometry = QApplication.primaryScreen().availableGeometry()
        if screen_geometry.width() >= 1920:
            self.resizeDocks([dock_statement_viewer], [670], Qt.Orientation.Horizontal)

    def connect_signals(self) -> None:
        """Connect signals to their respective slots."""
        self.exit_action.triggered.connect(self.on_exit)
        self.about_action.triggered.connect(self.on_about_action)
        self.github_action.triggered.connect(self.on_github_action)

    def on_exit(self) -> None:
        """Handle the exit action.

        Emit the exit signal and delegate the closing tasks to the controller.
        """
        self.exit_signal.emit()

    def on_about_action(self) -> None:
        """Handle the about action.

        Show the about dialog with information about the BRMS application.
        """
        from PySide6.QtWidgets import QMessageBox

        QMessageBox.about(self, "About BRMS", __about__)

    def on_github_action(self) -> None:
        """Handle the GitHub action.

        Open the GitHub page of the BRMS application in the default web browser.
        """
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices

        QDesktopServices.openUrl(QUrl(__github__))
