from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from brms.utils import qldate_to_pydate
from brms.views.base import BRMSDoubleSpinBox, BRMSWidget


class BaseCalculatorWidget(BRMSWidget):
    def __init__(self, parent=None, name="Calculator", size=(600, 560)):
        super().__init__(parent, Qt.WindowType.Window)
        self.setWindowTitle(name)
        self.setGeometry(100, 100, *size)
        self.center_window()


class BondCalculatorWidget(BaseCalculatorWidget):
    def __init__(self, parent=None):
        super().__init__(parent, name="Fixed-Rate Bond Calculator", size=(600, 560))

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
        self.payment_frequency_edit.addItems(
            ["Annually", "Semiannually", "Quarterly", "Monthly"]
        )
        self.payment_frequency_edit.setCurrentIndex(1)
        bond_features_layout.addRow(
            payment_frequency_label, self.payment_frequency_edit
        )

        calendar_label = QLabel("Calendar")
        self.calendar_edit = QComboBox()
        self.calendar_edit.addItems(["Null", "United States", "Australia"])
        bond_features_layout.addRow(calendar_label, self.calendar_edit)

        business_day_convention_label = QLabel("Business Day Convention")
        self.business_day_convention_edit = QComboBox()
        self.business_day_convention_edit.addItems(["Unadjusted", "Following"])
        self.business_day_convention_edit.setEnabled(False)
        bond_features_layout.addRow(
            business_day_convention_label, self.business_day_convention_edit
        )

        self.calendar_edit.currentTextChanged.connect(self.calendar_selection_changed)

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
        valuation_parameters_layout.addRow(
            settlement_days_label, self.settlement_days_edit
        )

        valuation_date_label = QLabel("Valuation Date")
        self.valuation_date_edit = QDateEdit()
        self.valuation_date_edit.setDate(self.issue_date_edit.date())
        valuation_parameters_layout.addRow(
            valuation_date_label, self.valuation_date_edit
        )

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

        self.yield_curve_edit.currentTextChanged.connect(
            lambda _: self.flat_yield_edit.setEnabled(
                self.yield_curve_edit.currentText() == "Flat"
            )
        )

        compounding_label = QLabel("Compounding")
        self.compounding_edit = QComboBox()
        self.compounding_edit.addItems(["Compounded", "Continuous"])
        valuation_parameters_layout.addRow(compounding_label, self.compounding_edit)

        compounding_freq_label = QLabel("Compounding Frequency")
        self.compounding_freq_edit = QComboBox()
        self.compounding_freq_edit.addItems(
            ["Annually", "Semiannually", "Quarterly", "Monthly"]
        )
        valuation_parameters_layout.addRow(
            compounding_freq_label, self.compounding_freq_edit
        )

        self.compounding_edit.currentTextChanged.connect(
            lambda _: self.compounding_freq_edit.setEnabled(
                self.compounding_edit.currentText() == "Compounded"
            )
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

    def calendar_selection_changed(self):
        """
        This method is called when the calendar selection is changed.
        It enables or disables the business day convention edit based on the selected calendar.
        If the selected calendar is "Null", the business day convention edit is disabled and set to "Unadjusted".
        Otherwise, the business day convention edit is enabled.
        """
        if self.calendar_edit.currentText() == "Null":
            self.business_day_convention_edit.setEnabled(False)
            self.business_day_convention_edit.setCurrentText("Unadjusted")
        else:
            self.business_day_convention_edit.setEnabled(True)

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
        table_widget.setVerticalHeaderLabels(
            ["NPV", "Clean Price", "Dirty Price", "Accrued Interest"]
        )
        npv_item = QTableWidgetItem(self.locale().toString(npv, "f", 2))
        clean_price_item = QTableWidgetItem(self.locale().toString(clean_price, "f", 2))
        dirty_price_item = QTableWidgetItem(self.locale().toString(dirty_price, "f", 2))
        accrued_interest_item = QTableWidgetItem(
            self.locale().toString(accrued_interest, "f", 2)
        )
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


class LoanCalculatorWidget(BaseCalculatorWidget):
    def __init__(self, parent=None):

        super().__init__(parent, name="Amortizing Loan Calculator", size=(1000, 560))

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

        maturity_label = QLabel("Maturity")
        self.maturity_edit = QSpinBox()
        self.maturity_edit.setValue(10)
        loan_features_layout.addRow(maturity_label, self.maturity_edit)

        maturity_unit_label = QLabel("Maturity Unit")
        self.maturity_unit_edit = QComboBox()
        self.maturity_unit_edit.addItems(["Years", "Months"])
        loan_features_layout.addRow(maturity_unit_label, self.maturity_unit_edit)

        interest_rate_label = QLabel("Interest rate")
        self.interest_rate_edit = BRMSDoubleSpinBox()
        self.interest_rate_edit.setDecimals(3)
        self.interest_rate_edit.setSuffix("%")
        self.interest_rate_edit.setValue(4)
        loan_features_layout.addRow(interest_rate_label, self.interest_rate_edit)

        payment_frequency_label = QLabel("Payment Frequency")
        self.payment_frequency_edit = QComboBox()
        self.payment_frequency_edit.addItems(
            ["Annually", "Semiannually", "Quarterly", "Monthly"]
        )
        self.payment_frequency_edit.setCurrentIndex(3)
        loan_features_layout.addRow(
            payment_frequency_label, self.payment_frequency_edit
        )

        calendar_label = QLabel("Calendar")
        self.calendar_edit = QComboBox()
        self.calendar_edit.addItems(["Null", "United States", "Australia"])
        loan_features_layout.addRow(calendar_label, self.calendar_edit)

        business_day_convention_label = QLabel("Business Day Convention")
        self.business_day_convention_edit = QComboBox()
        self.business_day_convention_edit.addItems(["Unadjusted", "Following"])
        self.business_day_convention_edit.setEnabled(False)
        loan_features_layout.addRow(
            business_day_convention_label, self.business_day_convention_edit
        )

        self.calendar_edit.currentTextChanged.connect(self.calendar_selection_changed)

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
        valuation_parameters_layout.addRow(
            settlement_days_label, self.settlement_days_edit
        )

        valuation_date_label = QLabel("Valuation Date")
        self.valuation_date_edit = QDateEdit()
        self.valuation_date_edit.setDate(self.issue_date_edit.date())
        valuation_parameters_layout.addRow(
            valuation_date_label, self.valuation_date_edit
        )

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

        self.yield_curve_edit.currentTextChanged.connect(
            lambda _: self.flat_yield_edit.setEnabled(
                self.yield_curve_edit.currentText() == "Flat"
            )
        )

        compounding_label = QLabel("Compounding")
        self.compounding_edit = QComboBox()
        self.compounding_edit.addItems(["Compounded", "Continuous"])
        valuation_parameters_layout.addRow(compounding_label, self.compounding_edit)

        compounding_freq_label = QLabel("Compounding Frequency")
        self.compounding_freq_edit = QComboBox()
        self.compounding_freq_edit.addItems(
            ["Annually", "Semiannually", "Quarterly", "Monthly"]
        )
        valuation_parameters_layout.addRow(
            compounding_freq_label, self.compounding_freq_edit
        )

        self.compounding_edit.currentTextChanged.connect(
            lambda _: self.compounding_freq_edit.setEnabled(
                self.compounding_edit.currentText() == "Compounded"
            )
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

    def calendar_selection_changed(self):
        """
        This method is called when the calendar selection is changed.
        It enables or disables the business day convention edit based on the selected calendar.
        If the selected calendar is "Null", the business day convention edit is disabled and set to "Unadjusted".
        Otherwise, the business day convention edit is enabled.
        """
        if self.calendar_edit.currentText() == "Null":
            self.business_day_convention_edit.setEnabled(False)
            self.business_day_convention_edit.setCurrentText("Unadjusted")
        else:
            self.business_day_convention_edit.setEnabled(True)

    def show_loan_payment_schedule(self, interest_pmt, principal_pmt, outstanding_amt):
        """
        Display the bond payment schedule in the table widget.
        """
        self.table_widget.clearContents()
        self.table_widget.setRowCount(len(interest_pmt))

        for row, (date, pmt) in enumerate(interest_pmt):
            weekday_string = qldate_to_pydate(date).strftime("%A")
            date_string = qldate_to_pydate(date).isoformat()
            pmt_item = QTableWidgetItem(self.locale().toString(pmt, "f", 2))
            pmt_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table_widget.setItem(row, 0, QTableWidgetItem(weekday_string))
            self.table_widget.setItem(row, 1, QTableWidgetItem(date_string))
            self.table_widget.setItem(row, 2, pmt_item)

        for row, (date, pmt) in enumerate(principal_pmt):
            pmt_item = QTableWidgetItem(self.locale().toString(pmt, "f", 2))
            pmt_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table_widget.setItem(row, 3, pmt_item)

        for row, (date, amt) in enumerate(outstanding_amt):
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
