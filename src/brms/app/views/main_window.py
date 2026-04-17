"""Main window class for the BRMS application."""

import qtawesome as qta
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QLabel,
    QMainWindow,
    QMenuBar,
    QSizePolicy,
    QSplitter,
    QStatusBar,
    QTabWidget,
    QToolBar,
    QWidget,
)

from brms import DEBUG_MODE, __about__, __github__, __homepage__, __version__
from brms.app.views.bank_book import BRMSCombinedBookWidget
from brms.app.views.calculators import BRMSBondCalculatorWidget, BRMSMortgageCalculatorWidget
from brms.app.views.dashboard import BRMSDashboard
from brms.app.views.inspector import BRMSInspectorWidget
from brms.app.views.interest_rate import BRMSInterestRateWidget
from brms.app.views.interest_rate_risk import BRMSInterestRateRiskWidget
from brms.app.views.rwa_credit_risk import BRMSRWACreditRiskWidget
from brms.app.views.statement_viewer import BRMSStatementViewer
from brms.app.views.styler import BRMSStyler
from brms.app.views.transaction_history import BRMSTransactionHistoryWidget
from brms.app.views.widgets.dock_widget import BRMSDockWidget
from brms.app.views.yield_curve import BRMSYieldCurveWidget
from brms.resources import icons  # noqa: F401

if DEBUG_MODE:
    from brms.app.views.debug_panel import DebugPanel


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
        self.combined_book_widget: BRMSCombinedBookWidget
        self.statement_viewer_widget: BRMSStatementViewer
        self._dock_widgets: list[BRMSDockWidget] = []
        self.yield_curve_widget = BRMSYieldCurveWidget(self)
        self.interest_rate_tab_widget = BRMSInterestRateWidget(self)
        self.bond_calculator_widget: BRMSBondCalculatorWidget | None = None
        self.mortgage_calculator_widget: BRMSMortgageCalculatorWidget | None = None
        self.transaction_history_widget: BRMSTransactionHistoryWidget
        self.rwa_credit_risk_widget: BRMSRWACreditRiskWidget
        self.interest_rate_risk_widget: BRMSInterestRateRiskWidget
        self.init_ui()
        self.connect_signals()
        # Actions
        self.new_action: QAction
        self.open_action: QAction
        self.save_action: QAction
        self.exit_action: QAction
        self.step_action: QAction
        self.run_action: QAction
        self.speed_combo: QComboBox
        self.stop_action: QAction
        self.tick_colors_action: QAction
        self.dashboard_action: QAction
        self.bank_book_action: QAction
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
        self.styler.apply_style()

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
        # Edit
        self.copy_value_action = QAction("Copy Value", self)
        self.copy_value_action.setShortcut("Ctrl+C")
        self.copy_row_action = QAction("Copy Row", self)
        self.copy_row_action.setShortcut("Ctrl+Shift+C")
        self.copy_details_action = QAction("Copy All Details", self)
        # Simulation
        self.step_action = QAction(qta.icon("mdi6.debug-step-over"), "Step", self)
        self.step_action.setShortcut("F2")
        self.step_action.setToolTip("Advance the simulation by one step (F2)")
        self.run_action = QAction(qta.icon("mdi6.play"), "Run", self)
        self.run_action.setShortcut("F3")
        self.run_action.setToolTip("Run the simulation continuously (F3)")
        self.stop_action = QAction(qta.icon("mdi6.stop"), "Stop", self)
        self.stop_action.setEnabled(False)
        self.speed_combo = QComboBox(self)
        self.speed_combo.addItems(["1x", "2x", "3x", "4x", "5x"])
        self.speed_combo.setCurrentText("1x")
        # Tick colors toggle
        self.tick_colors_action = QAction(
            qta.icon("mdi6.palette"), "Tick Colors", self,
        )
        self.tick_colors_action.setCheckable(True)
        self.tick_colors_action.setChecked(True)
        self.tick_colors_action.setToolTip("Show green/red colors for value changes")
        # View
        self.dashboard_action = QAction("Show Dashboard", self)
        self.dashboard_action.setShortcut("Ctrl+1")
        self.bank_book_action = QAction("Show Bank Book", self)
        self.bank_book_action.setShortcut("Ctrl+2")
        self.transaction_history_action = QAction("Show Transaction History", self)
        self.transaction_history_action.setShortcut("Ctrl+3")
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
        toolbar.addAction(self.step_action)
        toolbar.addAction(self.run_action)
        # Fix button widths so Run↔Pause label swap doesn't shift adjacent controls
        for action in (self.run_action, self.step_action):
            if (btn := toolbar.widgetForAction(action)) is not None:
                btn.setFixedWidth(90)
        toolbar.addSeparator()
        toolbar.addWidget(QLabel("  Speed: "))
        toolbar.addWidget(self.speed_combo)
        toolbar.addSeparator()
        toolbar.addAction(self.tick_colors_action)
        self.toolbar = toolbar
        # Per-tab actions are inserted after this separator when the active main
        # tab exposes a ``tab_actions`` list.
        self._tab_action_separator = toolbar.addSeparator()
        self._tab_action_separator.setVisible(False)
        self._current_tab_actions: list[QAction] = []

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
        # Edit menu
        edit_menu.addAction(self.copy_value_action)
        edit_menu.addAction(self.copy_row_action)
        edit_menu.addAction(self.copy_details_action)
        # View menu
        view_menu.addAction(self.dashboard_action)
        view_menu.addAction(self.bank_book_action)
        view_menu.addAction(self.transaction_history_action)
        view_menu.addAction(self.restore_views_action)
        # Simulation menu
        simulation_menu.addAction(self.step_action)
        simulation_menu.addAction(self.run_action)
        simulation_menu.addAction(self.stop_action)
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
        self.dashboard = BRMSDashboard()
        self.combined_book_widget = BRMSCombinedBookWidget()
        self.transaction_history_widget = BRMSTransactionHistoryWidget()
        self.rwa_credit_risk_widget = BRMSRWACreditRiskWidget()
        self.interest_rate_risk_widget = BRMSInterestRateRiskWidget()
        self.tab_widget.addTab(self.dashboard, "Dashboard")
        self.tab_widget.addTab(self.combined_book_widget, "Bank Book")
        self.tab_widget.addTab(self.transaction_history_widget, "Transaction History")
        self.tab_widget.addTab(self.rwa_credit_risk_widget, "RWA Credit Risk")
        self.tab_widget.addTab(self.interest_rate_risk_widget, "Interest Rate Risk")
        # Economic indicators at the bottom
        self.econ_indicator_tabs = QTabWidget(self)
        self.econ_indicator_tabs.addTab(self.yield_curve_widget, "Yield Curve")
        self.econ_indicator_tabs.addTab(self.interest_rate_tab_widget, "Interest Rate")
        self.econ_indicator_tabs.addTab(QWidget(), "Stock Market")
        # Vertical splitter: bank tabs on top, economic indicators on bottom
        self.tab_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Ignored)
        self.tab_widget.setMinimumHeight(self.window_height // 3)
        self.econ_indicator_tabs.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Ignored)
        self.econ_indicator_tabs.setMinimumHeight(self.window_height // 3)
        self.central_splitter = QSplitter(Qt.Orientation.Vertical)
        self.central_splitter.setChildrenCollapsible(False)
        self.central_splitter.addWidget(self.tab_widget)
        self.central_splitter.addWidget(self.econ_indicator_tabs)
        self.central_splitter.setStretchFactor(0, 1)
        self.central_splitter.setStretchFactor(1, 1)
        self.setCentralWidget(self.central_splitter)

    def create_dock_widgets(self) -> None:
        """Create and dock the inspector widget."""
        # Inspector
        self.dock_inspector = BRMSDockWidget("Inspector", self)
        self.inspector_widget = BRMSInspectorWidget(["Property", "Value"], self.dock_inspector)
        self.dock_inspector.setWidget(self.inspector_widget)
        self._dock_widgets.append(self.dock_inspector)
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
        self.restore_views_action.triggered.connect(self.on_restore_views)
        self.tick_colors_action.toggled.connect(self.styler.set_tick_colors)
        self.about_action.triggered.connect(self.on_about_action)
        self.homepage_action.triggered.connect(self.on_homepage_action)
        self.github_action.triggered.connect(self.on_github_action)
        self.bond_calculator_action.triggered.connect(self.toggle_bond_calculator)
        self.mortgage_calculator_action.triggered.connect(self.toggle_loan_calculator)
        self.dashboard_action.triggered.connect(lambda: self.tab_widget.setCurrentIndex(0))
        self.bank_book_action.triggered.connect(lambda: self.tab_widget.setCurrentIndex(1))
        self.transaction_history_action.triggered.connect(lambda: self.tab_widget.setCurrentIndex(2))
        self.tab_widget.currentChanged.connect(self._on_main_tab_changed)
        self._on_main_tab_changed(self.tab_widget.currentIndex())

    def _on_main_tab_changed(self, index: int) -> None:
        """Surface the active tab's ``tab_actions`` in the main toolbar."""
        for action in self._current_tab_actions:
            self.toolbar.removeAction(action)
        self._current_tab_actions = []
        widget = self.tab_widget.widget(index)
        actions = getattr(widget, "tab_actions", None) if widget is not None else None
        if actions:
            for action in actions:
                self.toolbar.addAction(action)
                self._current_tab_actions.append(action)
        self._tab_action_separator.setVisible(bool(self._current_tab_actions))

    def set_running_state(self, *, running: bool) -> None:
        """Swap the Run/Pause action between its two modes."""
        if running:
            self.run_action.setIcon(qta.icon("mdi6.pause"))
            self.run_action.setText("Pause")
            self.run_action.setShortcut("F4")
            self.run_action.setToolTip("Pause the simulation (F4)")
        else:
            self.run_action.setIcon(qta.icon("mdi6.play"))
            self.run_action.setText("Run")
            self.run_action.setShortcut("F3")
            self.run_action.setToolTip("Run the simulation continuously (F3)")

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

    def showEvent(self, event: object) -> None:  # noqa: N802
        """Set the central splitter to 2/3 top, 1/3 bottom after geometry is resolved."""
        super().showEvent(event)
        h = self.central_splitter.height()
        self.central_splitter.setSizes([h * 2 // 3, h // 3])

    def on_exit(self) -> None:
        """Handle the exit action.

        Emit the exit signal and delegate the closing tasks to the controller.
        """
        self.exit_signal.emit()

    def on_restore_views(self) -> None:
        """Restore the dock widgets to their default positions and sizes."""
        # Right dock: statement viewer on top, inspector on bottom
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dock_statement_viewer)
        self.splitDockWidget(self.dock_statement_viewer, self.dock_inspector, Qt.Orientation.Vertical)
        for widget in self._dock_widgets:
            widget.setFloating(False)
            widget.show()
        # Resize right dock: thinner width, inspector gets more height
        screen_geometry = QApplication.primaryScreen().availableGeometry()
        if screen_geometry.width() >= 1080:
            self.resizeDocks([self.dock_statement_viewer], [500], Qt.Orientation.Horizontal)
        self.resizeDocks(
            [self.dock_statement_viewer, self.dock_inspector], [400, 400], Qt.Orientation.Vertical,
        )

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
