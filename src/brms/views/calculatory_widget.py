import datetime

import pandas as pd
import qtawesome as qta
import QuantLib as ql
from dateutil.relativedelta import relativedelta
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter
from PySide6.QtCore import QDate, Qt, Signal
from PySide6.QtGui import QAction, QCloseEvent, QShowEvent
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from brms.accounting.statement_viewer import locale
from brms.instruments.factory import InstrumentFactory
from brms.utils import qdate_to_qldate, qldate_to_pydate
from brms.views.styler import BRMSStyler


class BRMSDoubleSpinBox(QDoubleSpinBox):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)

    def textFromValue(self, value):
        return self.locale().toString(value, "f", 2)


class BaseCalculatorWidget(QWidget):
    def __init__(self, parent=None, name="Calculator", size=(600, 560)):
        super().__init__(parent, Qt.WindowType.Window)
        self.setWindowTitle(name)
        self.setGeometry(100, 100, *size)
        self.center_window()

    def center_window(self) -> None:
        """Center the main window on the screen."""
        screen_geometry = QApplication.primaryScreen().availableGeometry()
        x = (screen_geometry.width() - self.geometry().width()) // 2
        y = (screen_geometry.height() - self.geometry().height()) // 2
        self.move(x, y)

    def show_warning(self, message="Error", informative_text=""):
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle("Warning")
        msg_box.setText(message)
        if len(informative_text):
            msg_box.setInformativeText(informative_text)
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec()

    def handle_calendar_selection_changed(self):
        if self.calendar_edit.currentText() == "Null":
            self.business_day_convention_edit.setEnabled(False)
            self.business_day_convention_edit.setCurrentText("Unadjusted")
        else:
            self.business_day_convention_edit.setEnabled(True)

    def handle_yield_curve_changed(self):
        self.flat_yield_edit.setEnabled(self.yield_curve_edit.currentText() == "Flat")


class BRMSBondCalculatorWidget(BaseCalculatorWidget):
    def __init__(self, parent=None):
        super().__init__(parent, name="Fixed-Rate Bond Calculator", size=(660, 560))

        # Create the form layout
        calculator_layout = QHBoxLayout()
        control_panel_layout = QVBoxLayout()
        control_panel_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # ======================================================================
        # Valuation parameters
        # ======================================================================
        # Create the upper group box for bond features
        bond_features_group_box = QGroupBox("Bond Features")
        bond_features_layout = QFormLayout()

        face_value_label = QLabel("Face Value")
        self.face_value_edit = BRMSDoubleSpinBox()
        self.face_value_edit.setDecimals(2)
        self.face_value_edit.setPrefix("$")
        self.face_value_edit.setMinimum(0)
        self.face_value_edit.setMaximum(100_000_000_000)
        self.face_value_edit.setValue(100)
        bond_features_layout.addRow(face_value_label, self.face_value_edit)

        issue_date_label = QLabel("Issue Date")
        self.issue_date_edit = QDateEdit()
        self.issue_date_edit.setDate(QDate(2021, 12, 19))
        bond_features_layout.addRow(issue_date_label, self.issue_date_edit)

        maturity_date_label = QLabel("Maturity Date")
        self.maturity_date_edit = QDateEdit()
        self.maturity_date_edit.setDate(QDate(2031, 12, 19))
        bond_features_layout.addRow(maturity_date_label, self.maturity_date_edit)

        interest_rate_label = QLabel("Interest rate")
        self.interest_rate_edit = BRMSDoubleSpinBox()
        self.interest_rate_edit.setDecimals(3)
        self.interest_rate_edit.setSuffix("%")
        self.interest_rate_edit.setValue(4)
        bond_features_layout.addRow(interest_rate_label, self.interest_rate_edit)

        payment_frequency_label = QLabel("Payment Frequency")
        self.payment_frequency_edit = QComboBox()
        self.payment_frequency_edit.addItems(["Annually", "Semiannually", "Quarterly", "Monthly"])
        self.payment_frequency_edit.setCurrentIndex(1)
        bond_features_layout.addRow(payment_frequency_label, self.payment_frequency_edit)

        calendar_label = QLabel("Calendar")
        self.calendar_edit = QComboBox()
        self.calendar_edit.addItems(["Null", "United States", "Australia"])
        bond_features_layout.addRow(calendar_label, self.calendar_edit)

        business_day_convention_label = QLabel("Business Day Convention")
        self.business_day_convention_edit = QComboBox()
        self.business_day_convention_edit.addItems(["Unadjusted", "Following"])
        self.business_day_convention_edit.setEnabled(False)
        bond_features_layout.addRow(business_day_convention_label, self.business_day_convention_edit)

        self.calendar_edit.currentTextChanged.connect(self.handle_calendar_selection_changed)

        date_generation_label = QLabel("Date Generation")
        self.date_generation_edit = QComboBox()
        self.date_generation_edit.addItems(["Backward", "Forward"])
        bond_features_layout.addRow(date_generation_label, self.date_generation_edit)

        bond_features_group_box.setLayout(bond_features_layout)

        # ======================================================================
        # Valuation parameters
        # ======================================================================
        # Create the lower group box for valuation parameters
        valuation_parameters_group_box = QGroupBox("Valuation Parameters")
        valuation_parameters_layout = QFormLayout()

        settlement_days_label = QLabel("Settlement Days")
        self.settlement_days_edit = QSpinBox()
        self.settlement_days_edit.setValue(0)
        valuation_parameters_layout.addRow(settlement_days_label, self.settlement_days_edit)

        valuation_date_label = QLabel("Valuation Date")
        self.valuation_date_edit = QDateEdit()
        self.valuation_date_edit.setDate(self.issue_date_edit.date())
        valuation_parameters_layout.addRow(valuation_date_label, self.valuation_date_edit)

        day_count_label = QLabel("Day Count")
        self.day_count_edit = QComboBox()
        self.day_count_edit.addItems(["30/360", "Actual/Actual"])
        valuation_parameters_layout.addRow(day_count_label, self.day_count_edit)

        yield_curve_label = QLabel("Yield Curve")
        self.yield_curve_edit = QComboBox()
        self.yield_curve_edit.addItems(["Flat"])
        self.yield_curve_edit.setEnabled(False)
        valuation_parameters_layout.addRow(yield_curve_label, self.yield_curve_edit)

        flat_yield_label = QLabel("Flat Yield")
        self.flat_yield_edit = BRMSDoubleSpinBox()
        self.flat_yield_edit.setDecimals(3)
        self.flat_yield_edit.setSuffix("%")
        self.flat_yield_edit.setValue(5)
        valuation_parameters_layout.addRow(flat_yield_label, self.flat_yield_edit)

        self.yield_curve_edit.currentTextChanged.connect(self.handle_yield_curve_changed)

        compounding_label = QLabel("Compounding")
        self.compounding_edit = QComboBox()
        self.compounding_edit.addItems(["Compounded", "Continuous"])
        valuation_parameters_layout.addRow(compounding_label, self.compounding_edit)

        compounding_freq_label = QLabel("Compounding Frequency")
        self.compounding_freq_edit = QComboBox()
        self.compounding_freq_edit.addItems(["Annually", "Semiannually", "Quarterly", "Monthly"])
        valuation_parameters_layout.addRow(compounding_freq_label, self.compounding_freq_edit)

        self.compounding_edit.currentTextChanged.connect(
            lambda _: self.compounding_freq_edit.setEnabled(self.compounding_edit.currentText() == "Compounded")
        )

        valuation_parameters_group_box.setLayout(valuation_parameters_layout)

        # ======================================================================
        # Stack together
        # ======================================================================
        # Add the group boxes to the form layout

        self.payments_button = QPushButton(text="Bond Payments")
        self.calculate_button = QPushButton(text="Calculate")
        self.calculate_button.setDefault(True)
        self.calculate_button.setFocus()

        control_panel_layout.addWidget(bond_features_group_box)
        control_panel_layout.addWidget(self.payments_button)
        control_panel_layout.addWidget(valuation_parameters_group_box)
        control_panel_layout.addWidget(self.calculate_button)

        calculator_layout.addLayout(control_panel_layout)

        # ======================================================================
        # Payment schedule table
        # ======================================================================
        self.table_widget = QTableWidget()
        self.table_widget.setAlternatingRowColors(True)
        self.table_widget.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table_widget.setColumnCount(3)
        self.table_widget.setHorizontalHeaderLabels(["Weekday", "Date", "Payment"])
        self.table_widget.resizeColumnsToContents()
        self.table_widget.horizontalHeader().setStretchLastSection(True)
        self.table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        calculator_layout.addWidget(self.table_widget)

        # Set the form layout as the main layout of the widget
        self.setLayout(calculator_layout)

        # ======================================================================
        # Connect signals
        # ======================================================================
        self.payments_button.clicked.connect(self.update_bond_payments_schedule)
        self.calculate_button.clicked.connect(self.update_bond_value)

    def show_bond_payment_schedule(self, payments):
        """
        Display the bond payment schedule in a table widget.

        This method retrieves the necessary parameters from the widget's input fields,
        calculates the bond payment schedule using the `fixed_rate_bond_payment_schedule` function,
        and populates a table widget with the payment schedule data.

        The table widget is assumed to be named `table_widget` and should have three columns:
        - Weekday: The weekday of the payment date.
        - Date: The payment date in ISO format.
        - Payment: The payment amount.

        Note: This method assumes that the necessary input fields and table widget have been properly initialized.
        """
        self.table_widget.clearContents()
        self.table_widget.setRowCount(len(payments))
        for row, (date, payment) in enumerate(payments):
            weekday_string = date.strftime("%A")
            date_string = date.isoformat()
            payment_item = QTableWidgetItem(self.locale().toString(payment, "f", 2))
            payment_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table_widget.setItem(row, 0, QTableWidgetItem(weekday_string))
            self.table_widget.setItem(row, 1, QTableWidgetItem(date_string))
            self.table_widget.setItem(row, 2, payment_item)

    def show_bond_value(self, npv, clean_price, dirty_price, accrued_interest):
        """
        Display the bond value in a dialog.

        This method calculates the bond value using the provided parameters and displays it in a dialog box.
        The bond value includes the NPV, clean price, dirty price, and accrued interest.
        """

        value_dialog = QDialog(self)
        value_dialog.setWindowTitle("Bond Value")
        layout = QVBoxLayout(value_dialog)
        table_widget = QTableWidget()
        table_widget.setEditTriggers(QTableWidget.NoEditTriggers)
        table_widget.setRowCount(4)
        table_widget.setColumnCount(1)
        table_widget.setVerticalHeaderLabels(["NPV", "Clean Price", "Dirty Price", "Accrued Interest"])
        npv_item = QTableWidgetItem(self.locale().toString(npv, "f", 2))
        clean_price_item = QTableWidgetItem(self.locale().toString(clean_price, "f", 2))
        dirty_price_item = QTableWidgetItem(self.locale().toString(dirty_price, "f", 2))
        accrued_interest_item = QTableWidgetItem(self.locale().toString(accrued_interest, "f", 2))
        npv_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        clean_price_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        dirty_price_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        accrued_interest_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        table_widget.setItem(0, 0, npv_item)
        table_widget.setItem(1, 0, clean_price_item)
        table_widget.setItem(2, 0, dirty_price_item)
        table_widget.setItem(3, 0, accrued_interest_item)
        table_widget.resizeColumnsToContents()
        table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table_widget.horizontalHeader().hide()

        layout.addWidget(table_widget)

        close_button = QPushButton("Close")
        close_button.clicked.connect(value_dialog.close)
        layout.addWidget(close_button)

        value_dialog.exec()

    def parse_view_params(self):
        """Parse the parameters from the widget inputs and return a tuple of values."""
        face_value = self.face_value_edit.value()
        settlement_days = self.settlement_days_edit.value()
        issue_date = qdate_to_qldate(self.issue_date_edit.date())
        maturity_date = qdate_to_qldate(self.maturity_date_edit.date())
        valuation_date = qdate_to_qldate(self.valuation_date_edit.date())
        coupon_rate = self.interest_rate_edit.value() / 100
        fixed_forward_rate = self.flat_yield_edit.value() / 100

        match self.date_generation_edit.currentText():
            case "Backward":
                date_generation = ql.DateGeneration.Backward
            case "Forward":
                date_generation = ql.DateGeneration.Forward

        match self.payment_frequency_edit.currentText():
            case "Annually":
                frequency = ql.Annual
            case "Semiannually":
                frequency = ql.Semiannual
            case "Quarterly":
                frequency = ql.Quarterly
            case "Monthly":
                frequency = ql.Monthly

        match self.compounding_freq_edit.currentText():
            case "Annually":
                comp_frequency = ql.Annual
            case "Semiannually":
                comp_frequency = ql.Semiannual
            case "Quarterly":
                comp_frequency = ql.Quarterly
            case "Monthly":
                comp_frequency = ql.Monthly

        match self.business_day_convention_edit.currentText():
            case "Unadjusted":
                business_convention = ql.Unadjusted
            case "Following":
                business_convention = ql.Following

        match self.calendar_edit.currentText():
            case "Null":
                calendar_ql = ql.NullCalendar()
            case "United States":
                calendar_ql = ql.UnitedStates(ql.UnitedStates.NYSE)
            case "Australia":
                calendar_ql = ql.Australia(ql.Australia.ASX)

        match self.day_count_edit.currentText():
            case "30/360":
                day_count = ql.Thirty360(ql.Thirty360.BondBasis)
            case "Actual/Actual":
                day_count = ql.ActualActual(ql.ActualActual.ISDA)

        match self.compounding_edit.currentText():
            case "Compounded":
                compounding = ql.Compounded
            case "Continuous":
                compounding = ql.Continuous

        return (
            valuation_date,
            fixed_forward_rate,
            compounding,
            comp_frequency,
            face_value,
            coupon_rate,
            issue_date,
            maturity_date,
            frequency,
            settlement_days,
            calendar_ql,
            day_count,
            business_convention,
            date_generation,
        )

    def build_bond(self):
        params = self.parse_view_params()
        (
            valuation_date,
            fixed_forward_rate,
            compounding,
            comp_frequency,
            face_value,
            coupon_rate,
            issue_date,
            maturity_date,
            frequency,
            settlement_days,
            calendar_ql,
            day_count,
            business_convention,
            date_generation,
        ) = params
        try:
            bond = InstrumentFactory.create_fixed_rate_bond(
                face_value=face_value,
                issue_date=qldate_to_pydate(issue_date),
                maturity_date=qldate_to_pydate(maturity_date),
                frequency=frequency,
                coupon_rate=coupon_rate,
                day_count=day_count,
                calendar=calendar_ql,
                business_convention=business_convention,
                date_generation=date_generation,
                settlement_days=settlement_days,
            )
        except RuntimeError as err:
            self.show_warning(str(err))
            return

        return bond, params

    def update_bond_payments_schedule(self):
        bond, params = self.build_bond()
        self.show_bond_payment_schedule(bond.payment_schedule())

        return bond, params

    def update_bond_value(self):
        # Update the bond payment schedule first
        bond, params = self.update_bond_payments_schedule()
        (
            valuation_date,
            fixed_forward_rate,
            compounding,
            comp_frequency,
            *_,
        ) = params

        # Value
        yield_curve = ql.FlatForward(
            valuation_date,
            ql.QuoteHandle(ql.SimpleQuote(fixed_forward_rate)),
            bond.instrument.dayCounter(),
            compounding,
            comp_frequency,
        )
        bond_engine = ql.DiscountingBondEngine(ql.YieldTermStructureHandle(yield_curve))

        bond.instrument.setPricingEngine(bond_engine)

        # Just being cautious, restore previous evaluation date afterwards
        old_evaluation_date = ql.Settings.instance().evaluationDate

        ql.Settings.instance().evaluationDate = valuation_date

        npv = bond.instrument.NPV()
        clean_price = bond.instrument.cleanPrice()
        dirty_price = bond.instrument.dirtyPrice()
        accrued_interest = bond.instrument.accruedAmount()

        ql.Settings.instance().evaluationDate = old_evaluation_date
        # Update bond value
        self.show_bond_value(npv, clean_price, dirty_price, accrued_interest)

        return bond, params


class BRMSMortgageCalculatorWidget(BaseCalculatorWidget):
    def __init__(self, parent=None, name="Mortgage Calculator", size=(1500, 500)):
        super().__init__(parent, name=name, size=size)
        self.init_ui()
        self.update_loan_payments_schedule()

    def init_ui(self):
        # ======================================================================
        # Valuation parameters
        # ======================================================================
        # Create the upper group box for bond features
        loan_features_group_box = QGroupBox("Loan Features")
        loan_features_layout = QFormLayout()

        face_value_label = QLabel("Face Value")
        self.face_value_edit = BRMSDoubleSpinBox()
        self.face_value_edit.setDecimals(2)
        self.face_value_edit.setPrefix("$")
        self.face_value_edit.setMinimum(0)
        self.face_value_edit.setMaximum(100_000_000_000)
        self.face_value_edit.setValue(1_000_000)
        loan_features_layout.addRow(face_value_label, self.face_value_edit)

        issue_date_label = QLabel("Issue Date")
        self.issue_date_edit = QDateEdit()
        self.issue_date_edit.setDate(QDate(2021, 12, 19))
        loan_features_layout.addRow(issue_date_label, self.issue_date_edit)

        maturity_label = QLabel("Maturity (Years)")
        self.maturity_edit = QSpinBox()
        self.maturity_edit.setValue(30)
        loan_features_layout.addRow(maturity_label, self.maturity_edit)

        interest_rate_label = QLabel("Interest rate")
        self.interest_rate_edit = BRMSDoubleSpinBox()
        self.interest_rate_edit.setDecimals(3)
        self.interest_rate_edit.setSuffix("%")
        self.interest_rate_edit.setValue(4)
        loan_features_layout.addRow(interest_rate_label, self.interest_rate_edit)

        payment_frequency_label = QLabel("Payment Frequency")
        self.payment_frequency_edit = QComboBox()
        self.payment_frequency_edit.addItems(["Annually", "Semiannually", "Quarterly", "Monthly"])
        self.payment_frequency_edit.setCurrentIndex(3)
        loan_features_layout.addRow(payment_frequency_label, self.payment_frequency_edit)

        calendar_label = QLabel("Calendar")
        self.calendar_edit = QComboBox()
        self.calendar_edit.addItems(["Null", "United States", "Australia"])
        loan_features_layout.addRow(calendar_label, self.calendar_edit)

        business_day_convention_label = QLabel("Business Day Convention")
        self.business_day_convention_edit = QComboBox()
        self.business_day_convention_edit.addItems(["Unadjusted", "Following"])
        self.business_day_convention_edit.setEnabled(False)
        loan_features_layout.addRow(business_day_convention_label, self.business_day_convention_edit)

        self.calendar_edit.currentTextChanged.connect(self.handle_calendar_selection_changed)

        loan_features_group_box.setLayout(loan_features_layout)

        # ======================================================================
        # Valuation parameters
        # ======================================================================
        # Create the lower group box for valuation parameters
        valuation_parameters_group_box = QGroupBox("Valuation Parameters")
        valuation_parameters_layout = QFormLayout()

        settlement_days_label = QLabel("Settlement Days")
        self.settlement_days_edit = QSpinBox()
        self.settlement_days_edit.setValue(0)
        valuation_parameters_layout.addRow(settlement_days_label, self.settlement_days_edit)

        valuation_date_label = QLabel("Valuation Date")
        self.valuation_date_edit = QDateEdit()
        self.valuation_date_edit.setDate(self.issue_date_edit.date())
        valuation_parameters_layout.addRow(valuation_date_label, self.valuation_date_edit)

        day_count_label = QLabel("Day Count")
        self.day_count_edit = QComboBox()
        self.day_count_edit.addItems(["30/360", "Actual/Actual"])
        valuation_parameters_layout.addRow(day_count_label, self.day_count_edit)

        yield_curve_label = QLabel("Yield Curve")
        self.yield_curve_edit = QComboBox()
        self.yield_curve_edit.addItems(["Flat"])
        self.yield_curve_edit.setEnabled(False)
        valuation_parameters_layout.addRow(yield_curve_label, self.yield_curve_edit)

        flat_yield_label = QLabel("Flat Yield")
        self.flat_yield_edit = BRMSDoubleSpinBox()
        self.flat_yield_edit.setDecimals(3)
        self.flat_yield_edit.setSuffix("%")
        self.flat_yield_edit.setValue(5)
        valuation_parameters_layout.addRow(flat_yield_label, self.flat_yield_edit)

        self.yield_curve_edit.currentTextChanged.connect(self.handle_yield_curve_changed)

        compounding_label = QLabel("Compounding")
        self.compounding_edit = QComboBox()
        self.compounding_edit.addItems(["Compounded", "Continuous"])
        valuation_parameters_layout.addRow(compounding_label, self.compounding_edit)

        compounding_freq_label = QLabel("Compounding Frequency")
        self.compounding_freq_edit = QComboBox()
        self.compounding_freq_edit.addItems(["Annually", "Semiannually", "Quarterly", "Monthly"])
        valuation_parameters_layout.addRow(compounding_freq_label, self.compounding_freq_edit)

        self.compounding_edit.currentTextChanged.connect(
            lambda _: self.compounding_freq_edit.setEnabled(self.compounding_edit.currentText() == "Compounded")
        )

        valuation_parameters_group_box.setLayout(valuation_parameters_layout)

        # ======================================================================
        # Stack together
        # ======================================================================
        # Add the group boxes to the form layout

        self.payments_button = QPushButton(text="Loan Payments and Balances")
        self.payments_button.setToolTip("Assuming equal amortizing payments per period")
        self.calculate_button = QPushButton(text="Calculate")
        self.calculate_button.setDefault(True)
        self.calculate_button.setFocus()

        self.control_panel = QWidget()
        control_panel_layout = QVBoxLayout()
        control_panel_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        control_panel_layout.addWidget(loan_features_group_box)
        control_panel_layout.addWidget(self.payments_button)
        control_panel_layout.addWidget(valuation_parameters_group_box)
        control_panel_layout.addWidget(self.calculate_button)
        self.control_panel.setLayout(control_panel_layout)

        # ======================================================================
        # Payment schedule table
        # ======================================================================
        self.payments_widget = PaymentsWidget(self)
        self.table_widget = self.payments_widget.table_widget  # convenient access

        # ======================================================================
        # Main layout as QSplitter
        # ======================================================================
        main_splitter = QSplitter()
        main_splitter.setOrientation(Qt.Orientation.Horizontal)
        main_splitter.addWidget(self.control_panel)
        main_splitter.addWidget(self.payments_widget)
        # Set relative sizes of statistics panel and display area
        main_splitter.setStretchFactor(1, 5)

        main_layout = QHBoxLayout()
        main_layout.addWidget(main_splitter)
        self.setLayout(main_layout)

        # ======================================================================
        # Connect signals
        # ======================================================================
        self.payments_button.clicked.connect(self.update_loan_payments_schedule)
        self.calculate_button.clicked.connect(self.update_loan_value)

    def show_loan_payment_schedule(self, interest_pmt, principal_pmt, outstanding_amt):
        """
        Display the bond payment schedule in the table widget.
        """
        self.table_widget.clearContents()
        self.table_widget.setRowCount(len(interest_pmt))

        for row, ((date, pmt_i), (_, pmt_p), (_, amt)) in enumerate(
            zip(interest_pmt, principal_pmt, outstanding_amt, strict=True)
        ):
            weekday_string = date.strftime("%A")
            date_string = date.isoformat()
            self.table_widget.setItem(row, 0, QTableWidgetItem(weekday_string))
            self.table_widget.setItem(row, 1, QTableWidgetItem(date_string))
            # total payment
            pmt_item = QTableWidgetItem(self.locale().toString(pmt_i + pmt_p, "f", 2))
            pmt_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table_widget.setItem(row, 2, pmt_item)
            # interest payment
            pmt_item = QTableWidgetItem(self.locale().toString(pmt_i, "f", 2))
            pmt_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table_widget.setItem(row, 3, pmt_item)
            # principal payment
            pmt_item = QTableWidgetItem(self.locale().toString(pmt_p, "f", 2))
            pmt_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table_widget.setItem(row, 4, pmt_item)
            # outstanding amount
            amt_item = QTableWidgetItem(self.locale().toString(amt, "f", 2))
            amt_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table_widget.setItem(row, 5, amt_item)

        # for row, (date, pmt) in enumerate(interest_pmt):
        #     weekday_string = date.strftime("%A")
        #     date_string = date.isoformat()
        #     pmt_item = QTableWidgetItem(self.locale().toString(pmt, "f", 2))
        #     pmt_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        #     self.table_widget.setItem(row, 0, QTableWidgetItem(weekday_string))
        #     self.table_widget.setItem(row, 1, QTableWidgetItem(date_string))

        #     self.table_widget.setItem(row, 3, pmt_item)

        # for row, (_, pmt) in enumerate(principal_pmt):
        #     pmt_item = QTableWidgetItem(self.locale().toString(pmt, "f", 2))
        #     pmt_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        #     self.table_widget.setItem(row, 4, pmt_item)

        # for row, (_, amt) in enumerate(outstanding_amt):
        #     amt_item = QTableWidgetItem(self.locale().toString(amt, "f", 2))
        #     amt_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        #     self.table_widget.setItem(row, 5, amt_item)

        # Update plot
        dates = [date for date, _ in interest_pmt]
        self.payments_widget.plot_widget.update_plot(
            start_date=min(dates),
            end_date=max(dates),
            dates=dates,
            interest_pmt=[pmt for _, pmt in interest_pmt],
            principal_pmt=[pmt for _, pmt in principal_pmt],
            outstanding_amt=[amt for _, amt in outstanding_amt],
            show_grid=True,
        )

    def show_loan_value(self, npv, total_interest_pmt, total_principal_pmt, total_pmt):
        """
        Display the bond value in a dialog.
        """
        value_dialog = QDialog(self)
        value_dialog.setWindowTitle("Loan Value")
        layout = QVBoxLayout(value_dialog)
        table_widget = QTableWidget()
        table_widget.setEditTriggers(QTableWidget.NoEditTriggers)
        table_widget.setRowCount(4)
        table_widget.setColumnCount(1)
        table_widget.setVerticalHeaderLabels(
            [
                "NPV",
                "Total Interest Payment",
                "Total Principal Payment",
                "Total Payment",
            ]
        )
        # fmt: off
        npv_item = QTableWidgetItem(self.locale().toString(npv, "f", 2))
        npv_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        pmt_i_item = QTableWidgetItem(self.locale().toString(total_interest_pmt, "f", 2))
        pmt_i_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        pmt_p_item = QTableWidgetItem(self.locale().toString(total_principal_pmt, "f", 2))
        pmt_p_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        pmt_t_item = QTableWidgetItem(self.locale().toString(total_pmt, "f", 2))
        pmt_t_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        # fmt: on
        table_widget.setItem(0, 0, npv_item)
        table_widget.setItem(1, 0, pmt_i_item)
        table_widget.setItem(2, 0, pmt_p_item)
        table_widget.setItem(3, 0, pmt_t_item)
        table_widget.resizeColumnsToContents()
        table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table_widget.horizontalHeader().hide()

        layout.addWidget(table_widget)

        close_button = QPushButton("Close")
        close_button.clicked.connect(value_dialog.close)
        layout.addWidget(close_button)

        value_dialog.exec()

    def parse_view_params(self):
        """Parse the parameters from the widget inputs and return a tuple of values."""
        face_value = self.face_value_edit.value()
        settlement_days = self.settlement_days_edit.value()
        maturity_years = self.maturity_edit.value()
        issue_date = qdate_to_qldate(self.issue_date_edit.date())
        valuation_date = qdate_to_qldate(self.valuation_date_edit.date())
        coupon_rate = self.interest_rate_edit.value() / 100
        fixed_forward_rate = self.flat_yield_edit.value() / 100

        match self.payment_frequency_edit.currentText():
            case "Annually":
                frequency = ql.Annual
            case "Semiannually":
                frequency = ql.Semiannual
            case "Quarterly":
                frequency = ql.Quarterly
            case "Monthly":
                frequency = ql.Monthly

        match self.compounding_freq_edit.currentText():
            case "Annually":
                comp_frequency = ql.Annual
            case "Semiannually":
                comp_frequency = ql.Semiannual
            case "Quarterly":
                comp_frequency = ql.Quarterly
            case "Monthly":
                comp_frequency = ql.Monthly

        match self.business_day_convention_edit.currentText():
            case "Unadjusted":
                business_convention = ql.Unadjusted
            case "Following":
                business_convention = ql.Following

        match self.calendar_edit.currentText():
            case "Null":
                calendar_ql = ql.NullCalendar()
            case "United States":
                calendar_ql = ql.UnitedStates(ql.UnitedStates.NYSE)
            case "Australia":
                calendar_ql = ql.Australia(ql.Australia.ASX)

        match self.day_count_edit.currentText():
            case "30/360":
                day_count = ql.Thirty360(ql.Thirty360.BondBasis)
            case "Actual/Actual":
                day_count = ql.ActualActual(ql.ActualActual.ISDA)

        match self.compounding_edit.currentText():
            case "Compounded":
                compounding = ql.Compounded
            case "Continuous":
                compounding = ql.Continuous

        return (
            valuation_date,
            fixed_forward_rate,
            compounding,
            comp_frequency,
            face_value,
            coupon_rate,
            issue_date,
            maturity_years,
            frequency,
            settlement_days,
            calendar_ql,
            day_count,
            business_convention,
        )

    def build_loan(self):
        params = self.parse_view_params()
        (
            valuation_date,
            fixed_forward_rate,
            compounding,
            comp_frequency,
            face_value,
            coupon_rate,
            issue_date,
            maturity,
            frequency,
            settlement_days,
            calendar_ql,
            day_count,
            business_convention,
        ) = params
        try:
            loan = InstrumentFactory.create_residential_mortgage(
                face_value=face_value,
                issue_date=qldate_to_pydate(issue_date),
                maturity_years=maturity,
                frequency=frequency,
                interest_rate=coupon_rate,
                day_count=day_count,
                calendar=calendar_ql,
                business_convention=business_convention,
                settlement_days=settlement_days,
            )
        except RuntimeError as err:
            self.show_warning(str(err))
            return

        return loan, params

    def update_loan_payments_schedule(self):
        loan, params = self.build_loan()
        interest_pmt, principal_pmt, outstanding_amt = loan.payment_schedule()
        self.show_loan_payment_schedule(interest_pmt, principal_pmt, outstanding_amt)

        return loan, params

    def update_loan_value(self):
        # Update the loan payment schedule first
        loan, params = self.update_loan_payments_schedule()
        interest_pmt, principal_pmt, outstanding_amt = loan.payment_schedule()

        total_interest_pmt = sum(pmt for date, pmt in interest_pmt)
        total_principal_pmt = sum(pmt for date, pmt in principal_pmt)
        (
            valuation_date,
            fixed_forward_rate,
            compounding,
            comp_frequency,
            *_,
        ) = params

        # Value
        yield_curve = ql.FlatForward(
            valuation_date,
            ql.QuoteHandle(ql.SimpleQuote(fixed_forward_rate)),
            loan.instrument.dayCounter(),
            compounding,
            comp_frequency,
        )
        bond_engine = ql.DiscountingBondEngine(ql.YieldTermStructureHandle(yield_curve))

        loan.instrument.setPricingEngine(bond_engine)

        # Just being cautious, restore previous evaluation date afterwards
        old_evaluation_date = ql.Settings.instance().evaluationDate

        ql.Settings.instance().evaluationDate = valuation_date

        npv = loan.instrument.NPV()

        ql.Settings.instance().evaluationDate = old_evaluation_date

        # Update loan value
        self.show_loan_value(
            npv,
            total_interest_pmt,
            total_principal_pmt,
            total_interest_pmt + total_principal_pmt,
        )

        return loan, params


class PaymentsWidget(QWidget):
    visibility_changed = Signal()

    def __init__(self, parent):
        super().__init__(parent)
        self.is_visible = False
        self.setWindowTitle("Mortgage Payments and Balances")

        self.toolbar = QToolBar()
        self.toolbar.setMovable(False)
        self.toolbar.setFloatable(False)
        self.toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)

        self.save_action = QAction(qta.icon("mdi6.export"), "Export Plot", self)
        self.table_action = QAction(qta.icon("mdi6.table-of-contents"), "Show Table", self)
        self.figure_action = QAction(qta.icon("mdi6.chart-bell-curve-cumulative"), "Show Plot", self)
        self.all_view_action = QAction(qta.icon("mdi.chart-multiple"), "Show Both", self)

        self.table_action.setCheckable(True)
        self.figure_action.setCheckable(True)
        self.all_view_action.setCheckable(True)

        self.toolbar.addAction(self.table_action)
        self.toolbar.addAction(self.figure_action)
        self.toolbar.addAction(self.all_view_action)
        self.toolbar.addAction(self.save_action)

        self.table_widget = QTableWidget()
        self.table_widget.setAlternatingRowColors(True)
        self.table_widget.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table_widget.setColumnCount(6)
        self.table_widget.setHorizontalHeaderLabels(
            [
                "Weekday",
                "Date",
                "Total Payment",
                "Interest Payment",
                "Principal Payment",
                "Outstanding Balance",
            ]
        )
        self.table_widget.resizeColumnsToContents()
        self.table_widget.horizontalHeader().setStretchLastSection(True)
        self.table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.plot_widget = PlotWidget(title="Mortgage Payments and Outstanding Balances", parent=self)

        self.splitter = QSplitter()
        self.splitter.setOrientation(Qt.Orientation.Vertical)
        self.splitter.addWidget(self.plot_widget)
        self.splitter.addWidget(self.table_widget)

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.toolbar)
        main_layout.addWidget(self.splitter)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.setLayout(main_layout)

        self.all_view_action.triggered.connect(self.set_default_view)
        self.table_action.triggered.connect(self.set_table_view)
        self.figure_action.triggered.connect(self.set_figure_view)
        self.save_action.triggered.connect(self.plot_widget.export_plot)

        self.set_figure_view()

    def set_default_view(self):
        self.all_view_action.setChecked(True)
        self.figure_action.setChecked(False)
        self.table_action.setChecked(False)
        total_size = 1000  # Arbitrary total size
        table_view_size = int(total_size * 0.5)
        plot_widget_size = total_size - table_view_size
        self.splitter.setSizes([table_view_size, plot_widget_size])

    def set_table_view(self):
        self.table_action.setChecked(True)
        self.figure_action.setChecked(False)
        self.all_view_action.setChecked(False)
        self.splitter.setSizes([0, 1])

    def set_figure_view(self):
        self.figure_action.setChecked(True)
        self.table_action.setChecked(False)
        self.all_view_action.setChecked(False)
        self.splitter.setSizes([1, 0])

    def showEvent(self, event: QShowEvent):
        self.is_visible = True
        self.visibility_changed.emit()
        super().showEvent(event)

    def closeEvent(self, event: QCloseEvent):
        self.is_visible = False
        self.visibility_changed.emit()
        super().closeEvent(event)


class PlotWidget(QWidget):
    def __init__(self, title: str = "", parent=None) -> None:
        super().__init__(parent)
        self.styler = BRMSStyler.instance()
        self.title = title
        self.start_date: datetime.date = datetime.date.today() - relativedelta(years=1)
        self.end_date: datetime.date = datetime.date.today()
        self.dates: list[datetime.date] = []
        self.values: list[float] = []
        self.show_grid = True

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.canvas = FigureCanvas(Figure(figsize=(5, 3), facecolor=self.styler.plot_background_color))
        layout.addWidget(self.canvas)
        self.ax = self.canvas.figure.add_subplot()
        self.ax.set_title(self.title)
        self.ax.set_ylabel("Payments")
        if self.show_grid:
            self.ax.grid(self.show_grid, linestyle="--", alpha=0.7)
        self.ax.tick_params(axis="both", which="major", labelsize=10)
        self.ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: locale.currency(x, grouping=True)))
        self.ax2 = self.ax.twinx()
        self.ax2.set_ylabel("Outstanding Balance")
        self.ax2.tick_params(axis="y")
        self.ax2.yaxis.set_major_formatter(FuncFormatter(lambda x, _: locale.currency(x, grouping=True)))
        # Checkboxes
        checkbox_layout = QHBoxLayout()
        checkbox_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        # Add checkbox for controlling grid lines
        self.grid_checkbox = QCheckBox("Show Grid Lines", self)
        self.grid_checkbox.setChecked(True)  # Default to showing grid lines
        checkbox_layout.addWidget(self.grid_checkbox)
        layout.addLayout(checkbox_layout)
        # Data containers
        (self.line_interest_pmt,) = self.ax.plot([], [], color="blue", label="Interest Payment")
        (self.line_principal_pmt,) = self.ax.plot([], [], color="red", label="Principal Payment")
        (self.line_total_pmt,) = self.ax.plot([], [], color="darkred", label="Total Payment")
        (self.line_outstanding_amt,) = self.ax2.plot([], [], color="black", linestyle="--", label="Outstanding Balance")
        # Signals
        self.grid_checkbox.stateChanged.connect(self.on_grid_checkbox_state_changed)
        self.styler.style_changed.connect(self.update_plot_style)

    def update_plot_style(self):
        """Update an existing Matplotlib figure when the style changes."""
        if self.styler.use_custom_style:
            self.canvas.figure.patch.set_facecolor(self.styler.plot_background_color)  # Update figure background
        else:
            self.canvas.figure.patch.set_facecolor("white")  # Default background
        self.canvas.figure.canvas.draw_idle()  # Redraw canvas

    def on_grid_checkbox_state_changed(self) -> None:
        self.update_plot(
            self.start_date,
            self.end_date,
            self.dates,
            self.interest_pmt,
            self.principal_pmt,
            self.outstanding_amt,
            self.grid_checkbox.isChecked(),
        )

    def clear_plot(self) -> None:
        self.ax.clear()
        self.ax.set_title(self.title)
        self.canvas.draw()

    def update_plot(
        self,
        start_date: datetime.date,
        end_date: datetime.date,
        dates: list[datetime.date],
        interest_pmt: list[float],
        principal_pmt: list[float],
        outstanding_amt: list[float],
        show_grid: bool,
    ) -> None:
        self.start_date = start_date
        self.end_date = end_date
        self.dates = dates
        self.interest_pmt = interest_pmt
        self.principal_pmt = principal_pmt
        self.outstanding_amt = outstanding_amt
        self.show_grid = show_grid

        self.ax.set_xlim(pd.Timestamp(start_date), pd.Timestamp(end_date))
        if show_grid:
            # When line properties are provided, the grid will be enabled regardless.
            self.ax.grid(True, linestyle="--", alpha=0.7)
        else:
            self.ax.grid(False)

        if dates and interest_pmt and principal_pmt and outstanding_amt:
            self.line_interest_pmt.set_data(dates, interest_pmt)
            self.line_principal_pmt.set_data(dates, principal_pmt)
            self.line_total_pmt.set_data(dates, interest_pmt + principal_pmt)
            self.line_total_pmt.set_data(dates, [i + p for i, p in zip(interest_pmt, principal_pmt)])
            self.line_outstanding_amt.set_data(dates, outstanding_amt)
            # Recalculate limits and autoscale view
            # self.ax.relim()
            self.ax.set_ylim(0.0, 2 * max(principal_pmt, default=0))
            self.ax.autoscale_view()
            self.ax2.set_ylim(0.0, 1.1 * max(outstanding_amt, default=0))
            self.ax2.autoscale_view()

        if max(principal_pmt, default=0) >= 1_000_000:
            formatter = FuncFormatter(lambda x, _: locale.currency(x / 1_000_000, grouping=True) + "M")
        elif max(principal_pmt, default=0) >= 1_000:
            formatter = FuncFormatter(lambda x, _: locale.currency(x / 1_000, grouping=True) + "K")
        else:
            formatter = FuncFormatter(lambda x, _: locale.currency(x, grouping=True))
        self.ax.yaxis.set_major_formatter(formatter)

        if max(outstanding_amt, default=0) >= 1_000_000:
            formatter = FuncFormatter(lambda x, _: locale.currency(x / 1_000_000, grouping=True) + "M")
        elif max(outstanding_amt, default=0) >= 1_000:
            formatter = FuncFormatter(lambda x, _: locale.currency(x / 1_000, grouping=True) + "K")
        else:
            formatter = FuncFormatter(lambda x, _: locale.currency(x, grouping=True))
        self.ax2.yaxis.set_major_formatter(formatter)

        if dates:
            self.ax.legend(fontsize=9, loc="upper right")
            self.ax2.legend(fontsize=9, loc="upper left")

        self.canvas.draw_idle()

    def export_plot(self):
        options = QFileDialog.Options()
        plot_title = self.ax.get_title()
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            caption="Save Plot",
            dir=f"BRMS - {plot_title}",
            filter="PNG Files (*.png);;All Files (*)",
            options=options,
        )
        if file_path:
            self.canvas.figure.savefig(file_path)
