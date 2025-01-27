"""Main window class for the BRMS application."""

import qtawesome as qta
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QMenuBar,
    QStatusBar,
    QStyleFactory,
    QTabWidget,
    QToolBar,
    QWidget,
)

from brms import DEBUG_MODE, __about__, __github__, __version__
from brms.resources import icons  # noqa: F401
from brms.views.bank_book_widget import BRMSBankingBookWidget, BRMSTradingBookWidget
from brms.views.dashboard_widget import BRMSDashboard
from brms.views.dock_widget import BRMSDockWidget
from brms.views.inspector_widget import BRMSInspectorWidget
from brms.views.statement_viewer_widget import BRMSStatementViewer
from brms.views.yield_curve_widget import BRMSYieldCurveWidget


class MainWindow(QMainWindow):
    """Main window class for the BRMS application."""

    exit_signal = Signal()

    def __init__(self) -> None:
        """Initialize the main window."""
        super().__init__()
        self.read_settings()
        # UI components
        self.dashboard: BRMSDashboard
        self.inspector_widget: BRMSInspectorWidget
        self.banking_book_widget: BRMSBankingBookWidget
        self.trading_book_widget: BRMSTradingBookWidget
        self.statement_viewer_widget: BRMSStatementViewer
        self._dock_widgets: list[BRMSDockWidget] = []
        self.yield_curve_widget = BRMSYieldCurveWidget(self)
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
        self.speed_up_action: QAction
        self.speed_down_action: QAction
        self.stop_action: QAction
        self.fushion_style_action: QAction
        self.mq_style_action: QAction
        self.restore_views_action: QAction
        self.about_action: QAction
        self.github_action: QAction

        if DEBUG_MODE:
            from brms.views.debug_panel import DebugPanel

            self.debug_panel = DebugPanel(self)

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
        self.dashboard = BRMSDashboard()
        tab_widget.addTab(self.dashboard, "Dashboard")
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
        debug_notice = " [Debug Mode] " if DEBUG_MODE else ""
        self.setWindowTitle(f"BRMS - Bank Risk Management Simulation v{__version__}{debug_notice}")
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
        # File
        self.new_action = QAction("New", self)
        self.open_action = QAction("Open", self)
        self.save_action = QAction("Save", self)
        self.exit_action = QAction(qta.icon("mdi6.exit-run"), "Exit", self)
        self.exit_action.setShortcut("Ctrl+Q")
        # Simulation
        self.next_action = QAction(qta.icon("mdi6.skip-next"), "Next", self)
        self.start_action = QAction(qta.icon("mdi6.play"), "Start", self)
        self.pause_action = QAction(qta.icon("mdi6.pause"), "Pause", self)
        self.stop_action = QAction(qta.icon("mdi6.stop"), "Stop", self)
        self.pause_action.setEnabled(False)
        self.stop_action.setEnabled(False)
        self.speed_up_action = QAction(qta.icon("mdi6.plus"), "Speed Up", self)
        self.speed_down_action = QAction(qta.icon("mdi6.minus"), "Speed Down", self)
        # View
        self.fushion_style_action = QAction("Fushion Theme", self)
        self.mq_style_action = QAction("MQ Theme", self)
        self.fushion_style_action.setCheckable(True)
        self.mq_style_action.setCheckable(True)
        self.restore_views_action = QAction("Restore Views", self)
        # Misc
        self.about_action = QAction("About", self)
        self.github_action = QAction(qta.icon("mdi6.github"), "GitHub", self)

    def create_toolbar(self) -> None:
        """Create the toolbar for the main window."""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        # Add actions to the toolbar
        toolbar.addAction(self.next_action)
        toolbar.addAction(self.start_action)
        toolbar.addAction(self.pause_action)
        toolbar.addAction(self.speed_up_action)
        toolbar.addAction(self.speed_down_action)

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
        # View menu
        view_menu.addAction(self.fushion_style_action)
        view_menu.addAction(self.mq_style_action)
        view_menu.addSeparator()
        view_menu.addAction(self.restore_views_action)
        # Simulation menu
        simulation_menu.addAction(self.next_action)
        simulation_menu.addAction(self.start_action)
        simulation_menu.addAction(self.pause_action)
        simulation_menu.addSeparator()
        simulation_menu.addAction(self.speed_up_action)
        simulation_menu.addAction(self.speed_down_action)
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
        self.dock_inspector = BRMSDockWidget("Inspector", self)
        self.inspector_widget = BRMSInspectorWidget(["Property", "Value"], self.dock_inspector)
        self.dock_inspector.setWidget(self.inspector_widget)
        self._dock_widgets.append(self.dock_inspector)
        # Economic indicator
        self.dock_econ_indicator = BRMSDockWidget("Economic Indicators", self)
        econ_indicator_widget = QTabWidget()
        econ_indicator_widget.addTab(self.yield_curve_widget, "Yield Curve")
        econ_indicator_widget.addTab(QWidget(), "Stock Market")
        self.dock_econ_indicator.setWidget(econ_indicator_widget)  # TODO: placeholder widget
        self._dock_widgets.append(self.dock_econ_indicator)
        # Statements viewer
        self.dock_statement_viewer = BRMSDockWidget("Financial Statements", self)
        self.dock_statement_viewer.setMinimumWidth(400)
        self.statement_viewer_widget = BRMSStatementViewer()
        self.dock_statement_viewer.setWidget(self.statement_viewer_widget)
        self._dock_widgets.append(self.dock_statement_viewer)
        # Call on_restore_views to place dock widgets at default positions
        self.on_restore_views()

    def apply_fushion_style(self):
        self.fushion_style_action.setChecked(True)
        self.mq_style_action.setChecked(False)
        self.setStyleSheet("")
        QApplication.instance().setStyle(QStyleFactory.create("Fusion"))

    def apply_mq_style(self):
        self.mq_style_action.setChecked(True)
        self.fushion_style_action.setChecked(False)
        # MQ's style guide
        # https://gem.mq.edu.au/guidelines
        Color_Red = "#A6192E"
        Color_Charcoal = "#373A36"
        Color_Sand_Light = "#EDEBE5"
        Color_Purple = "#80225F"
        Color_Deep_Red = "#76232F"
        Color_Bright_Red = "#D6001C"
        Color_Magenta = "#C6007E"
        Color_Success = "#009174"
        Color_Alert = "#BC4700"
        Color_Information = "#415364"
        Color_Sand = "#D6D2C4"
        Color_Dark_Purple = "#6F1D46"

        darker_sand = "#C0BEB0"  # Slightly darker than Color_Sand

        app_style = f"""
        QWidget {{
            background-color: {Color_Sand_Light};
            color: {Color_Charcoal};
        }}
        QDockWidget::title {{
            background-color: {Color_Sand};
            padding-top: 1px;
            padding-bottom: 1px;
            color: {Color_Sand_Light};
        }}
        QTabBar::tab {{
            background: {Color_Sand};
            color: {Color_Charcoal};
            border-bottom: 1px solid {Color_Sand_Light};
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
            min-width: 12ex;
            padding: 5px;
            padding-left: 10px;
            padding-right: 10px;
            margin-top: 5px;
            margin-right: 1px;
        }}
        QTabBar::tab::bottom {{
            background: {Color_Sand};
            color: {Color_Charcoal};
            border-top: 1px solid {Color_Sand_Light};
            border-top-left-radius: 0px;
            border-top-right-radius: 0px;
            border-bottom-left-radius: 4px;
            border-bottom-right-radius: 4px;
            min-width: 12ex;
            padding: 5px;
            padding-left: 10px;
            padding-right: 10px;
            margin-top: 0px;
            margin-bottom: 5px;
            margin-right: 1px;
        }}
        QTabBar::tab:selected {{
            background: {Color_Deep_Red};
            color: {Color_Sand_Light};
        }}
        QTabBar::tab:hover {{
            background: {Color_Red};
            color: {Color_Sand_Light};
        }}
        QPushButton {{
            background-color: {Color_Information};
            color: {Color_Sand_Light};
            border-radius: 5px;
            padding: 5px;
        }}
        QPushButton:hover {{
            background-color: {Color_Purple};
        }}
        QPushButton:pressed {{
            background-color: {Color_Dark_Purple};
        }}
        QMenuBar {{
            background-color: {Color_Charcoal};
            color: {Color_Sand_Light};
        }}
        QMenuBar::item {{
            background-color: {Color_Charcoal};
            color: {Color_Sand_Light};
            padding-left: 10px;
            padding-right: 10px;
            padding-top: 5px;
            padding-bottom: 5px;
        }}
        QMenuBar::item:selected {{
            background-color: {Color_Purple};
        }}
        QMenu {{
            background-color: {Color_Charcoal};
            color: {Color_Sand_Light};
        }}
        QMenu::item:selected {{
            background-color: {Color_Purple};
        }}
        QToolBar {{
            background-color: {Color_Sand_Light};
        }}
        QToolBar QWidget {{
            background-color: {Color_Sand_Light};
        }}
        QToolButton {{
            background-color: {Color_Sand};
        }}
        QToolButton:hover {{
            background-color: {Color_Red};
            color: {Color_Sand_Light};
        }}
        QHeaderView::section {{
            background-color: {Color_Sand};
            border: none;
            padding: 3px;
        }}
        QTableCornerButton::section {{
            background-color: {Color_Sand};
        }}
        QTreeView::item:selected {{
            background-color: {Color_Alert};
            color: {Color_Sand_Light};
        }}
        QTableView::item:selected {{
            background-color: {Color_Alert};
            color: {Color_Sand_Light};
        }}
        """
        self.setStyleSheet(app_style)

    def connect_signals(self) -> None:
        """Connect signals to their respective slots."""
        self.exit_action.triggered.connect(self.on_exit)
        self.fushion_style_action.triggered.connect(self.on_fushion_style_action)
        self.mq_style_action.triggered.connect(self.on_mq_style_action)
        self.restore_views_action.triggered.connect(self.on_restore_views)
        self.about_action.triggered.connect(self.on_about_action)
        self.github_action.triggered.connect(self.on_github_action)

    def on_exit(self) -> None:
        """Handle the exit action.

        Emit the exit signal and delegate the closing tasks to the controller.
        """
        self.exit_signal.emit()

    def on_fushion_style_action(self) -> None:
        """Handle the Fushion style action.

        Apply or remove the Fushion style based on the action's checked state.
        """
        if self.fushion_style_action.isChecked():
            self.apply_fushion_style()

    def on_mq_style_action(self) -> None:
        """Handle the MQ style action.

        Apply or remove the MQ style based on the action's checked state.
        """
        if self.mq_style_action.isChecked():
            self.apply_mq_style()

    def on_restore_views(self) -> None:
        """Restore the dock widgets to their default positions and sizes."""
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dock_econ_indicator)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dock_statement_viewer)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dock_inspector)
        for widget in self._dock_widgets:
            widget.setFloating(False)
            widget.show()
        # Resize statement viewer when user's screen size is large enough
        screen_geometry = QApplication.primaryScreen().availableGeometry()
        if screen_geometry.width() >= 1920:
            self.resizeDocks([self.dock_statement_viewer], [670], Qt.Orientation.Horizontal)
        # Resize dock widgets to make them equal height
        self.resizeDocks([self.dock_econ_indicator, self.dock_statement_viewer], [1, 1], Qt.Orientation.Vertical)
        self.tabifyDockWidget(self.dock_statement_viewer, self.dock_inspector)
        self.dock_statement_viewer.raise_()

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
