"""Main window class for the BRMS application."""

import qtawesome as qta
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QMenuBar,
    QStatusBar,
    QTabWidget,
    QToolBar,
    QWidget,
)

from brms import DEBUG_MODE, __about__, __github__, __homepage__, __version__
from brms.resources import icons  # noqa: F401
from brms.views.bank_book_widget import BRMSBankingBookWidget, BRMSTradingBookWidget
from brms.views.calculatory_widget import BRMSBondCalculatorWidget, BRMSMortgageCalculatorWidget
from brms.views.dashboard_widget import BRMSDashboard
from brms.views.dock_widget import BRMSDockWidget
from brms.views.inspector_widget import BRMSInspectorWidget
from brms.views.rwa_credit_risk_widget import BRMSRWACreditRiskWidget
from brms.views.statement_viewer_widget import BRMSStatementViewer
from brms.views.styler import BRMSStyler
from brms.views.transaction_history_widget import BRMSTransactionHistoryWidget
from brms.views.yield_curve_widget import BRMSYieldCurveWidget

if DEBUG_MODE:
    from brms.views.debug_panel import DebugPanel


class MainWindow(QMainWindow):
    """Main window class for the BRMS application."""

    exit_signal = Signal()

    def __init__(self) -> None:
        """Initialize the main window."""
        super().__init__()
        self.read_settings()
        self.styler = BRMSStyler.instance()
        # UI components
        self.dashboard: BRMSDashboard
        self.inspector_widget: BRMSInspectorWidget
        self.banking_book_widget: BRMSBankingBookWidget
        self.trading_book_widget: BRMSTradingBookWidget
        self.statement_viewer_widget: BRMSStatementViewer
        self._dock_widgets: list[BRMSDockWidget] = []
        self.yield_curve_widget = BRMSYieldCurveWidget(self)
        self.bond_calculator_widget: BRMSBondCalculatorWidget | None = None
        self.mortgage_calculator_widget: BRMSMortgageCalculatorWidget | None = None
        self.transaction_history_widget: BRMSTransactionHistoryWidget
        self.rwa_credit_risk_widget: BRMSRWACreditRiskWidget
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
        self.dashboard_action: QAction
        self.banking_book_action: QAction
        self.trading_book_action: QAction
        self.transaction_history_action: QAction
        self.restore_views_action: QAction
        self.bond_calculator_action: QAction
        self.mortgage_calculator_action: QAction
        self.about_action: QAction
        self.homepage_action: QAction
        self.github_action: QAction
        if DEBUG_MODE:
            self.debug_panel = DebugPanel(self)
        # Finalize
        self.on_mq_style_action()

    def init_ui(self) -> None:
        """Initialize the user interface."""
        self.set_window_properties()
        self.create_actions()
        self.create_menubar()
        self.create_toolbar()
        self.create_statusbar()
        self.create_central_widget()
        self.create_dock_widgets()

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
        self.dashboard_action = QAction("Show Dashboard", self)
        self.dashboard_action.setShortcut("Ctrl+1")
        self.banking_book_action = QAction("Show Banking Book", self)
        self.banking_book_action.setShortcut("Ctrl+2")
        self.trading_book_action = QAction("Show Trading Book", self)
        self.trading_book_action.setShortcut("Ctrl+3")
        self.transaction_history_action = QAction("Show Transaction History", self)
        self.transaction_history_action.setShortcut("Ctrl+4")
        self.restore_views_action = QAction("Restore Views", self)
        # Calculator
        self.bond_calculator_action = QAction("Fixed-Rate Bond Calculator", self)
        self.mortgage_calculator_action = QAction("Mortgage Calculator", self)
        self.bond_calculator_action.setCheckable(True)
        self.mortgage_calculator_action.setCheckable(True)
        self.bond_calculator_action.setChecked(False)
        self.mortgage_calculator_action.setChecked(False)
        # Misc
        self.about_action = QAction("About", self)
        self.homepage_action = QAction(qta.icon("mdi6.web"), "BankRisk.org", self)
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
        calculator_menu = menubar.addMenu("Calculator")
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
        view_menu.addAction(self.dashboard_action)
        view_menu.addAction(self.banking_book_action)
        view_menu.addAction(self.trading_book_action)
        view_menu.addAction(self.transaction_history_action)
        view_menu.addAction(self.restore_views_action)
        # Simulation menu
        simulation_menu.addAction(self.next_action)
        simulation_menu.addAction(self.start_action)
        simulation_menu.addAction(self.pause_action)
        simulation_menu.addSeparator()
        simulation_menu.addAction(self.speed_up_action)
        simulation_menu.addAction(self.speed_down_action)
        # Calculator menu
        calculator_menu.addAction(self.bond_calculator_action)
        calculator_menu.addAction(self.mortgage_calculator_action)
        # Help menu
        help_menu.addAction(self.about_action)
        help_menu.addAction(self.homepage_action)
        help_menu.addAction(self.github_action)

    def create_statusbar(self) -> None:
        """Create the status bar for the main window."""
        statusbar = QStatusBar(self)
        self.setStatusBar(statusbar)
        statusbar.showMessage("Ready")

    def create_central_widget(self) -> None:
        """Create the central widget."""
        self.tab_widget = QTabWidget(self)
        self.banking_book_widget = BRMSBankingBookWidget()
        self.trading_book_widget = BRMSTradingBookWidget()
        self.dashboard = BRMSDashboard()
        self.transaction_history_widget = BRMSTransactionHistoryWidget()
        self.rwa_credit_risk_widget = BRMSRWACreditRiskWidget()
        self.tab_widget.addTab(self.dashboard, "Dashboard")
        self.tab_widget.addTab(self.banking_book_widget, "Banking Book")
        self.tab_widget.addTab(self.trading_book_widget, "Trading Book")
        self.tab_widget.addTab(self.transaction_history_widget, "Transaction History")
        self.tab_widget.addTab(self.rwa_credit_risk_widget, "RWA Credit Risk")
        self.setCentralWidget(self.tab_widget)

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

    def connect_signals(self) -> None:
        """Connect signals to their respective slots."""
        self.exit_action.triggered.connect(self.on_exit)
        self.fushion_style_action.triggered.connect(self.on_fushion_style_action)
        self.mq_style_action.triggered.connect(self.on_mq_style_action)
        self.restore_views_action.triggered.connect(self.on_restore_views)
        self.about_action.triggered.connect(self.on_about_action)
        self.homepage_action.triggered.connect(self.on_homepage_action)
        self.github_action.triggered.connect(self.on_github_action)
        self.bond_calculator_action.triggered.connect(self.toggle_bond_calculator)
        self.mortgage_calculator_action.triggered.connect(self.toggle_loan_calculator)
        self.dashboard_action.triggered.connect(lambda: self.tab_widget.setCurrentIndex(0))
        self.banking_book_action.triggered.connect(lambda: self.tab_widget.setCurrentIndex(1))
        self.trading_book_action.triggered.connect(lambda: self.tab_widget.setCurrentIndex(2))
        self.transaction_history_action.triggered.connect(lambda: self.tab_widget.setCurrentIndex(3))

    def toggle_bond_calculator(self):
        if self.bond_calculator_action.isChecked():
            if self.bond_calculator_widget is None:
                self.bond_calculator_widget = BRMSBondCalculatorWidget(self)
                self.bond_calculator_widget.closeEvent = self.uncheck_bond_calculator_action
            self.bond_calculator_widget.show()
        else:
            self.bond_calculator_widget.close()

    def toggle_loan_calculator(self):
        if self.mortgage_calculator_action.isChecked():
            if self.mortgage_calculator_widget is None:
                self.mortgage_calculator_widget = BRMSMortgageCalculatorWidget(self)
                self.mortgage_calculator_widget.closeEvent = self.uncheck_mortgage_calculator_action
            self.mortgage_calculator_widget.show()
        else:
            self.mortgage_calculator_widget.close()

    def uncheck_bond_calculator_action(self, event):
        self.bond_calculator_action.setChecked(False)
        event.accept()

    def uncheck_mortgage_calculator_action(self, event):
        self.mortgage_calculator_action.setChecked(False)
        event.accept()

    def on_exit(self) -> None:
        """Handle the exit action.

        Emit the exit signal and delegate the closing tasks to the controller.
        """
        self.exit_signal.emit()

    def on_fushion_style_action(self) -> None:
        """Handle the Fushion style action.

        Apply or remove the Fushion style based on the action's checked state.
        """
        self.fushion_style_action.setChecked(True)
        self.mq_style_action.setChecked(False)
        self.styler.apply_fusion_style()

    def on_mq_style_action(self) -> None:
        """Handle the MQ style action.

        Apply or remove the MQ style based on the action's checked state.
        """
        self.mq_style_action.setChecked(True)
        self.fushion_style_action.setChecked(False)
        self.styler.apply_mq_style()

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
        if screen_geometry.width() >= 1080:
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

    def on_homepage_action(self) -> None:
        """Handle the homepage action.

        Open the homepage of the BRMS application in the default web browser.
        """
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices

        QDesktopServices.openUrl(QUrl(__homepage__))

    def on_github_action(self) -> None:
        """Handle the GitHub action.

        Open the GitHub page of the BRMS application in the default web browser.
        """
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices

        QDesktopServices.openUrl(QUrl(__github__))
