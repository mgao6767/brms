from PySide6.QtCore import QUrl
from PySide6.QtGui import QAction, QDesktopServices, QFont, QIcon, Qt
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from brms import __about__, __github__, __version__
from brms.controllers import (
    BondCalculatorController,
    LoanCalculatorController,
)
from brms.models import YieldCurveModel
from brms.views import (
    BankBooksWidget,
    BondCalculatorWidget,
    LoanCalculatorWidget,
    YieldCurveWidget,
)

from brms.resources import resource  # noqa isort:skip


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self._all_actions = []

        self.read_settings()
        self.set_window_properties()
        self.center_window()
        self.create_actions()
        self.create_menu_bar()
        self.create_toolbars()
        self.create_status_bar()
        self.apply_styles()

        # fmt: off
        self.bond_calculator = BondCalculatorWidget(self)
        self.loan_calculator = LoanCalculatorWidget(self)
        self.bond_calculator_ctrl = BondCalculatorController(self.bond_calculator)
        self.loan_calculator_ctrl = LoanCalculatorController(self.loan_calculator)

        self.bank_books_widget = BankBooksWidget(self, Qt.WindowType.Widget)

        # self.yield_curve_model = YieldCurveModel()
        self.yield_curve_widget = YieldCurveWidget(self)
        # self.yield_curve_ctrl = YieldCurveController(self.yield_curve_model, self.yield_curve_widget)
        # fmt: on

        self.create_central_widget()
        self.connect_signals_slots()

    def read_settings(self):
        # Read and apply settings here
        self.window_width = 1280
        self.window_height = 720

    def set_window_properties(self):
        self.setWindowTitle(f"BRMS - Bank Risk Management Simulation v{__version__}")
        self.setWindowIcon(QIcon(":/icons/icon.png"))
        self.setGeometry(100, 100, self.window_width, self.window_height)
        self.setMinimumSize(800, 600)

    def center_window(self):
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        window_geometry = self.frameGeometry()
        window_geometry.moveCenter(screen_geometry.center())
        self.move(window_geometry.topLeft())

    def create_actions(self):
        # fmt: off
        self.new_action = QAction("New simulation", self)
        self.open_action = QAction("Load scenario", self)
        self.save_action = QAction("Save", self)
        self.exit_action = QAction("Exit", self)
        self.exit_action.setShortcut("Ctrl+Q")
        self.start_action = QAction(QIcon.fromTheme("media-playback-start"), "Start", self)
        self.pause_action = QAction(QIcon.fromTheme("media-playback-pause"), "Pause", self)
        self.stop_action = QAction(QIcon.fromTheme("media-playback-stop"), "Stop", self)
        self.next_action = QAction(QIcon.fromTheme("media-skip-forward"), "Next", self)
        self.risk_metrics_action = QAction(QIcon(":/icons/bar-chart.png"), "Risk Metrics", self)
        self.stress_test_action = QAction(QIcon.fromTheme("dialog-warning"), "Stress Test", self)
        self.mgmt_action = QAction(QIcon.fromTheme("computer"), "Management", self)
        self.log_action = QAction(QIcon.fromTheme("document-new"), "Log", self)
        self.fullscreen_action = QAction("Full Screen", self)
        self.yield_curve_action = QAction(QIcon(":/icons/line-chart.png"), "Yield Curve", self)
        self.bond_calculator_action = QAction("Fixed-Rate Bond Calculator", self)
        self.loan_calculator_action = QAction("Amortizing Loan Calculator", self)
        self.about_action = QAction("About", self)        
        self.about_qt_action = QAction("About Qt", self)
        self.github_action = QAction("Project GitHub", self)
        self.speed_up_action = QAction(QIcon(":/icons/plus-key.png"), "Speed Up", self)
        self.speed_down_action = QAction(QIcon(":/icons/minus-key.png"), "Slow Down", self)
        self.next_action.setToolTip("Advance to next period in the simulation")
        self.mgmt_action.setToolTip("Take actions to manage risk")
        # fmt: on

        self._all_actions.extend(
            [
                self.new_action,
                self.open_action,
                self.save_action,
                self.exit_action,
                self.next_action,
                self.start_action,
                self.pause_action,
                self.stop_action,
                self.speed_up_action,
                self.speed_down_action,
                self.risk_metrics_action,
                self.stress_test_action,
                self.mgmt_action,
                self.log_action,
                self.fullscreen_action,
                self.yield_curve_action,
                self.bond_calculator_action,
                self.loan_calculator_action,
                self.about_action,
                self.about_qt_action,
                self.github_action,
            ]
        )
        for action in self._all_actions:
            action.setIconVisibleInMenu(False)

        # At init, only allow Next or Start.
        self.pause_action.setDisabled(True)
        self.stop_action.setDisabled(True)

        self.fullscreen_action.setCheckable(True)
        self.fullscreen_action.setChecked(False)
        self.bond_calculator_action.setCheckable(True)
        self.bond_calculator_action.setChecked(False)
        self.loan_calculator_action.setCheckable(True)
        self.loan_calculator_action.setChecked(False)
        # fmt: on

    def create_menu_bar(self):
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("File")
        edit_menu = menu_bar.addMenu("Edit")
        view_menu = menu_bar.addMenu("View")
        calc_menu = menu_bar.addMenu("Calculator")
        help_menu = menu_bar.addMenu("Help")

        # File menu
        file_menu.addAction(self.new_action)
        file_menu.addAction(self.open_action)
        file_menu.addAction(self.save_action)
        file_menu.addAction(self.exit_action)

        # Edit menu
        edit_menu.addAction(self.next_action)
        edit_menu.addAction(self.start_action)
        edit_menu.addAction(self.pause_action)
        edit_menu.addAction(self.stop_action)

        # View menu
        view_menu.addAction(self.yield_curve_action)
        view_menu.addAction(self.risk_metrics_action)
        view_menu.addAction(self.stress_test_action)
        view_menu.addAction(self.mgmt_action)
        view_menu.addAction(self.log_action)
        view_menu.addSeparator()
        view_menu.addAction(self.fullscreen_action)

        # Calculator menu
        calc_menu.addAction(self.bond_calculator_action)
        calc_menu.addAction(self.loan_calculator_action)

        # Help menu
        help_menu.addAction(self.github_action)
        help_menu.addSeparator()
        help_menu.addAction(self.about_action)
        help_menu.addAction(self.about_qt_action)

    def create_toolbars(self):

        self.toolbar = self.addToolBar("Toolbar")
        self.toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)

        self.toolbar.addAction(self.next_action)
        self.toolbar.addAction(self.start_action)
        self.toolbar.addAction(self.pause_action)
        self.toolbar.addAction(self.stop_action)
        self.toolbar.addAction(self.speed_up_action)
        self.toolbar.addAction(self.speed_down_action)

        self.toolbar.addSeparator()
        self.toolbar.addAction(self.yield_curve_action)
        self.toolbar.addAction(self.risk_metrics_action)
        self.toolbar.addAction(self.stress_test_action)
        self.toolbar.addAction(self.mgmt_action)

        self.toolbar.addSeparator()
        self.toolbar.addAction(self.log_action)

    def create_status_bar(self):
        self.statusBar = self.statusBar()
        self.statusBar.showMessage("Ready")

    def create_central_widget(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # fmt: off
        self.bank_books_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout = QVBoxLayout()
        top_panel_layout = QHBoxLayout()
        top_panel_layout.setAlignment(Qt.AlignLeft)
        self.current_date_label = QLabel()
        self.simulation_speed_label = QLabel()

        top_panel_layout.addWidget(self.simulation_speed_label)
        top_panel_layout.addWidget(QLabel("|"))
        top_panel_layout.addWidget(self.current_date_label)
        layout.addLayout(top_panel_layout)
        layout.addWidget(self.bank_books_widget)
        central_widget.setLayout(layout)

    def apply_styles(self):

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

        app_font = QFont("Work Sans", 10)
        QApplication.setFont(app_font)

        app_style = f"""
        QWidget {{
            background-color: {Color_Sand_Light};
            color: {Color_Charcoal};
        }}
        QPushButton {{
            background-color: {Color_Success};
            color: {Color_Sand_Light};
            border: 1px solid {Color_Charcoal};
            padding: 5px;
        }}
        QPushButton:hover {{
            background-color: {Color_Alert};
        }}
        QPushButton:pressed {{
            background-color: {Color_Deep_Red};
        }}
        QMenuBar {{
            background-color: {Color_Charcoal};
            color: {Color_Sand_Light};
        }}
        QMenuBar::item {{
            background-color: {Color_Charcoal};
            color: {Color_Sand_Light};
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
            background-color: {Color_Sand};
        }}
        QToolBar QWidget {{
            background-color: {Color_Sand};
        }}
        QToolButton {{
            background-color: {Color_Sand};
        }}
        QToolButton:hover {{
            background-color: {Color_Red};
            color: {Color_Sand_Light};
        }}
        QStatusBar {{
            background-color: {Color_Sand};
            color: {Color_Charcoal};
        }}
        QHeaderView::section {{
            background-color: {Color_Sand};
            border: none;
            padding: 3px;
        }}
        QTableCornerButton::section {{
            background-color: {Color_Sand};
        }}
        """
        self.setStyleSheet(app_style)

    def connect_signals_slots(self):
        self.github_action.triggered.connect(self.open_github)
        self.about_qt_action.triggered.connect(QApplication.instance().aboutQt)
        self.about_action.triggered.connect(self.show_about_dialog)
        self.fullscreen_action.triggered.connect(self.toggle_fullscreen)
        self.bond_calculator_action.triggered.connect(self.toggle_bond_calculator)
        self.loan_calculator_action.triggered.connect(self.toggle_loan_calculator)
        self.bond_calculator.closeEvent = self.uncheck_bond_calculator_action
        self.loan_calculator.closeEvent = self.uncheck_loan_calculator_action

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.statusBar.showMessage("Restored normal view.")
            self.showNormal()
        else:
            self.statusBar.showMessage("Entered full-screen view.")
            self.showFullScreen()

    def toggle_bond_calculator(self):
        if self.bond_calculator_action.isChecked():
            self.bond_calculator.show()
        else:
            self.bond_calculator.close()

    def toggle_loan_calculator(self):
        if self.loan_calculator_action.isChecked():
            self.loan_calculator.show()
        else:
            self.loan_calculator.close()

    def uncheck_bond_calculator_action(self, event):
        self.bond_calculator_action.setChecked(False)
        event.accept()

    def uncheck_loan_calculator_action(self, event):
        self.loan_calculator_action.setChecked(False)
        event.accept()

    def show_about_dialog(self):
        QMessageBox.about(self, "About BRMS", __about__)

    def open_github(self):
        QDesktopServices.openUrl(QUrl(__github__))

    def show_warning(self, message="Error", informative_text=""):
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle("Warning")
        msg_box.setText(message)
        if len(informative_text):
            msg_box.setInformativeText(informative_text)
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec()
