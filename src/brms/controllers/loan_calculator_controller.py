import QuantLib as ql

from brms.models.instruments import InstrumentFactory
from brms.utils import qdate_to_qldate
from brms.views import LoanCalculatorWidget


class LoanCalculatorController:
    def __init__(self, view: LoanCalculatorWidget):
        self.view = view
        self.view.payments_button.clicked.connect(self.update_loan_payments_schedule)
        self.view.calculate_button.clicked.connect(self.update_loan_value)

    def parse_view_params(self):
        """
        Parse the parameters from the widget inputs and return a tuple of values.

        Returns:
            Tuple: A tuple containing the parsed parameter values in the following order:
                - valuation_date (ql.Date): The valuation date of the bond.
                - fixed_forward_rate (float): The fixed forward rate of the bond.
                - compounding (ql.Compounding): The compounding method for interest calculation.
                - comp_frequency (ql.Frequency): The compounding frequency for interest calculation.
                - face_value (float): The face value of the bond.
                - coupon_rate (float): The coupon rate of the bond.
                - issue_date (ql.Date): The issue date of the bond.
                - maturity (ql.Period): The maturity of the bond.
                - frequency (ql.Frequency): The payment frequency of the bond.
                - settlement_days (int): The number of settlement days for the bond.
                - calendar_ql (ql.Calendar): The calendar used for date calculations.
                - day_count (ql.DayCounter): The day count convention for interest calculation.
                - business_convention (ql.BusinessDayConvention): The business day convention for date adjustment.
        """
        face_value = self.view.face_value_edit.value()
        settlement_days = self.view.settlement_days_edit.value()
        maturity_n = self.view.maturity_edit.value()
        issue_date = qdate_to_qldate(self.view.issue_date_edit.date())
        valuation_date = qdate_to_qldate(self.view.valuation_date_edit.date())
        coupon_rate = self.view.interest_rate_edit.value() / 100
        fixed_forward_rate = self.view.flat_yield_edit.value() / 100

        match self.view.payment_frequency_edit.currentText():
            case "Annually":
                frequency = ql.Annual
            case "Semiannually":
                frequency = ql.Semiannual
            case "Quarterly":
                frequency = ql.Quarterly
            case "Monthly":
                frequency = ql.Monthly

        match self.view.maturity_unit_edit.currentText():
            case "Years":
                maturity = ql.Period(maturity_n, ql.Years)
            case "Months":
                maturity = ql.Period(maturity_n, ql.Months)

        match self.view.compounding_freq_edit.currentText():
            case "Annually":
                comp_frequency = ql.Annual
            case "Semiannually":
                comp_frequency = ql.Semiannual
            case "Quarterly":
                comp_frequency = ql.Quarterly
            case "Monthly":
                comp_frequency = ql.Monthly

        match self.view.business_day_convention_edit.currentText():
            case "Unadjusted":
                business_convention = ql.Unadjusted
            case "Following":
                business_convention = ql.Following

        match self.view.calendar_edit.currentText():
            case "Null":
                calendar_ql = ql.NullCalendar()
            case "United States":
                calendar_ql = ql.UnitedStates(ql.UnitedStates.NYSE)
            case "Australia":
                calendar_ql = ql.Australia(ql.Australia.ASX)

        match self.view.day_count_edit.currentText():
            case "30/360":
                day_count = ql.Thirty360(ql.Thirty360.BondBasis)
            case "Actual/Actual":
                day_count = ql.ActualActual(ql.ActualActual.ISDA)

        match self.view.compounding_edit.currentText():
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
            maturity,
            frequency,
            settlement_days,
            calendar_ql,
            day_count,
            business_convention,
        )

    def build_loan(self):

        params = self.parse_view_params()
        try:
            loan = InstrumentFactory.create_fixed_rate_amortizing_loan(*params[4:])
        except RuntimeError as err:
            self.view.show_warning(str(err))
            return

        return loan, params

    def update_loan_payments_schedule(self):

        loan, params = self.build_loan()
        interest_pmt, principal_pmt, outstanding_amt = loan.payment_schedule()
        self.view.show_loan_payment_schedule(
            interest_pmt, principal_pmt, outstanding_amt
        )

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

        # Update loan value
        npv, _, _, _ = loan.value(
            valuation_date, fixed_forward_rate, compounding, comp_frequency
        )
        self.view.show_loan_value(
            npv,
            total_interest_pmt,
            total_principal_pmt,
            total_interest_pmt + total_principal_pmt,
        )

        return loan, params
