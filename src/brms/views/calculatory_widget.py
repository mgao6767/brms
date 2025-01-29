import QuantLib as ql
from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDateEdit,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from brms.instruments.factory import InstrumentFactory
from brms.utils import qdate_to_qldate, qldate_to_pydate


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
            weekday_string = qldate_to_pydate(date).strftime("%A")
            date_string = qldate_to_pydate(date).isoformat()
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


class BRMSLoanCalculatorWidget(BaseCalculatorWidget):
    def __init__(self, parent=None):
        super().__init__(parent, name="Amortizing Loan Calculator", size=(1100, 500))

        # Create the form layout
        calculator_layout = QHBoxLayout()
        control_panel_layout = QVBoxLayout()

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
        self.face_value_edit.setValue(100_000)
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

        control_panel_layout.addWidget(loan_features_group_box)
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
        self.table_widget.setColumnCount(5)
        self.table_widget.setHorizontalHeaderLabels(
            [
                "Weekday",
                "Date",
                "Interest Payment",
                "Principal Payment",
                "Outstanding Balance",
            ]
        )
        self.table_widget.resizeColumnsToContents()
        self.table_widget.horizontalHeader().setStretchLastSection(True)
        self.table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        calculator_layout.addWidget(self.table_widget)

        # Set the form layout as the main layout of the widget
        self.setLayout(calculator_layout)

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

        for row, (date, pmt) in enumerate(interest_pmt):
            weekday_string = date.strftime("%A")
            date_string = date.isoformat()
            pmt_item = QTableWidgetItem(self.locale().toString(pmt, "f", 2))
            pmt_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table_widget.setItem(row, 0, QTableWidgetItem(weekday_string))
            self.table_widget.setItem(row, 1, QTableWidgetItem(date_string))
            self.table_widget.setItem(row, 2, pmt_item)

        for row, (_, pmt) in enumerate(principal_pmt):
            pmt_item = QTableWidgetItem(self.locale().toString(pmt, "f", 2))
            pmt_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table_widget.setItem(row, 3, pmt_item)

        for row, (_, amt) in enumerate(outstanding_amt):
            amt_item = QTableWidgetItem(self.locale().toString(amt, "f", 2))
            amt_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table_widget.setItem(row, 4, amt_item)

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
