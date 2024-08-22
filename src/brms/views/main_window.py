from PySide6.QtGui import QAction, QIcon, Qt
from PySide6.QtWidgets import QApplication, QMainWindow, QWidgetAction, QLabel

from brms.controllers import BondCalculatorController, LoanCalculatorController
from brms.models import BondModel, LoanModel
from brms.views import BankBooksWidget, BondCalculatorWidget, LoanCalculatorWidget

from brms.resources import resource  # noqa isort:skip


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.read_settings()
        self.set_window_properties()
        self.center_window()
        self.create_menu_bar()
        self.create_toolbars()
        self.create_status_bar()
        self.create_dock_widgets()
        self.apply_styles()

        self.bond_model = BondModel()
        self.bond_calculator_widget = BondCalculatorWidget(self)
        self.bond_calculator_controller = BondCalculatorController(
            self.bond_model, self.bond_calculator_widget
        )

        self.loan_model = LoanModel()
        self.loan_calculator_widget = LoanCalculatorWidget(self)
        self.loan_calculator_controller = LoanCalculatorController(
            self.loan_model, self.loan_calculator_widget
        )

        self.bank_books_widget = BankBooksWidget(self, Qt.WindowType.Widget)

        self.create_central_widget()
        self.connect_signals_slots()

    def read_settings(self):
        # Read and apply settings here
        self.window_width = 1280
        self.window_height = 720

    def set_window_properties(self):
        self.setWindowTitle("BRMS - Bank Risk Management Simulation")
        self.setWindowIcon(QIcon(":/icons/icon.png"))
        self.setGeometry(100, 100, self.window_width, self.window_height)
        self.setMinimumSize(800, 600)

    def center_window(self):
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        window_geometry = self.frameGeometry()
        window_geometry.moveCenter(screen_geometry.center())
        self.move(window_geometry.topLeft())

    def create_menu_bar(self):
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("File")
        edit_menu = menu_bar.addMenu("Edit")
        view_menu = menu_bar.addMenu("View")
        calc_menu = menu_bar.addMenu("Calculator")
        help_menu = menu_bar.addMenu("Help")

        # File menu
        self.new_action = QAction("New", self)
        self.open_action = QAction("Open", self)
        self.save_action = QAction("Save", self)
        self.exit_action = QAction("Exit", self)
        self.exit_action.setShortcut("Ctrl+Q")

        file_menu.addAction(self.new_action)
        file_menu.addAction(self.open_action)
        file_menu.addAction(self.save_action)
        file_menu.addAction(self.exit_action)

        # Edit menu
        self.start_action = QAction(
            QIcon.fromTheme("media-playback-start"), "Start", self
        )
        self.pause_action = QAction(
            QIcon.fromTheme("media-playback-pause"), "Pause", self
        )
        self.stop_action = QAction(QIcon.fromTheme("media-playback-stop"), "Stop", self)
        self.next_action = QAction(QIcon.fromTheme("media-skip-forward"), "Next", self)
        self.next_action.setToolTip("Advance to next period in the simulation")

        self.start_action.setIconVisibleInMenu(False)
        self.next_action.setIconVisibleInMenu(False)
        self.pause_action.setIconVisibleInMenu(False)
        self.stop_action.setIconVisibleInMenu(False)
        self.pause_action.setDisabled(True)
        self.stop_action.setDisabled(True)
        edit_menu.addAction(self.next_action)
        edit_menu.addAction(self.start_action)
        edit_menu.addAction(self.pause_action)
        edit_menu.addAction(self.stop_action)

        # View menu
        self.risk_metrics_action = QAction(
            QIcon.fromTheme("dialog-information"), "Risk Metrics", self
        )
        self.stress_test_action = QAction(
            QIcon.fromTheme("dialog-warning"), "Stress Test", self
        )
        self.mgmt_action = QAction(QIcon.fromTheme("computer"), "Management", self)
        self.mgmt_action.setToolTip("Take actions to manage risk")

        self.log_action = QAction(QIcon.fromTheme("document-new"), "Log", self)

        self.risk_metrics_action.setIconVisibleInMenu(False)
        self.stress_test_action.setIconVisibleInMenu(False)
        self.mgmt_action.setIconVisibleInMenu(False)
        self.log_action.setIconVisibleInMenu(False)

        self.fullscreen_action = QAction("Full Screen", self)
        self.fullscreen_action.setCheckable(True)
        self.fullscreen_action.setChecked(False)

        view_menu.addAction(self.risk_metrics_action)
        view_menu.addAction(self.stress_test_action)
        view_menu.addAction(self.mgmt_action)
        view_menu.addAction(self.log_action)
        view_menu.addSeparator()
        view_menu.addAction(self.fullscreen_action)

        # Calculator menu
        self.bond_calculator_action = QAction("Fixed-Rate Bond Calculator", self)
        self.bond_calculator_action.setCheckable(True)
        self.bond_calculator_action.setChecked(False)
        self.loan_calculator_action = QAction("Amortizing Loan Calculator", self)
        self.loan_calculator_action.setCheckable(True)
        self.loan_calculator_action.setChecked(False)

        calc_menu.addAction(self.bond_calculator_action)
        calc_menu.addAction(self.loan_calculator_action)

        # Help menu
        pass

    def create_toolbars(self):

        self.toolbar = self.addToolBar("Toolbar")
        self.toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)

        section1_label = QLabel("Simulation: ")
        section1_action = QWidgetAction(self)
        section1_action.setDefaultWidget(section1_label)
        self.toolbar.addAction(section1_action)
        self.toolbar.addAction(self.next_action)
        self.toolbar.addAction(self.start_action)
        self.toolbar.addAction(self.pause_action)
        self.toolbar.addAction(self.stop_action)

        self.toolbar.addSeparator()
        section2_label = QLabel("Risk Management: ")
        section2_action = QWidgetAction(self)
        section2_action.setDefaultWidget(section2_label)
        self.toolbar.addAction(section2_action)
        self.toolbar.addAction(self.risk_metrics_action)
        self.toolbar.addAction(self.stress_test_action)
        self.toolbar.addAction(self.mgmt_action)
        self.toolbar.addSeparator()

        self.toolbar.addAction(self.log_action)

    def create_status_bar(self):
        self.statusBar = self.statusBar()
        self.statusBar.showMessage("Ready")

    def create_central_widget(self):
        self.setCentralWidget(self.bank_books_widget)

    def create_dock_widgets(self):
        # Create dockable widgets here
        pass

    def apply_styles(self):
        pass

    def connect_signals_slots(self):
        """
        Connects the signals and slots for the main window.

        This method connects the signals emitted by various UI elements in the main window
        to their corresponding slots, which are responsible for handling the events.
        """
        self.exit_action.triggered.connect(self.close)
        self.fullscreen_action.triggered.connect(self.toggle_fullscreen)
        self.bond_calculator_action.triggered.connect(self.toggle_bond_calculator)
        self.loan_calculator_action.triggered.connect(self.toggle_loan_calculator)
        self.bond_calculator_widget.closeEvent = self.uncheck_bond_calculator_action
        self.loan_calculator_widget.closeEvent = self.uncheck_loan_calculator_action

    def toggle_fullscreen(self):
        """
        Toggles the fullscreen mode of the main window.

        If the window is currently in fullscreen mode, it will be restored to its normal size.
        If the window is currently in normal size, it will be switched to fullscreen mode.
        """
        if self.isFullScreen():
            self.statusBar.showMessage("Restored normal view.")
            self.showNormal()
        else:
            self.statusBar.showMessage("Entered full-screen view.")
            self.showFullScreen()

    def toggle_bond_calculator(self):
        if self.bond_calculator_action.isChecked():
            self.bond_calculator_widget.show()
        else:
            self.bond_calculator_widget.close()

    def toggle_loan_calculator(self):
        if self.loan_calculator_action.isChecked():
            self.loan_calculator_widget.show()
        else:
            self.loan_calculator_widget.close()

    def uncheck_bond_calculator_action(self, event):
        self.bond_calculator_action.setChecked(False)
        event.accept()

    def uncheck_loan_calculator_action(self, event):
        self.loan_calculator_action.setChecked(False)
        event.accept()
