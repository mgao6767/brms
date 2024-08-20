import QuantLib as ql

from .bond_model import BondModel


class LoanModel(BondModel):

    def __init__(self) -> None:
        pass

    def build_amortizing_bond(
        self,
        face_value: float,
        interest_rate: float,
        issue_date: ql.Date,
        maturity: ql.Period,
        frequency: ql.Period = ql.Semiannual,
        settlement_days: int = 0,
        calendar: ql.Calendar = ql.NullCalendar(),
        day_count: ql.DayCounter = ql.Thirty360(ql.Thirty360.BondBasis),
        business_convention=ql.Unadjusted,
    ) -> ql.AmortizingFixedRateBond:

        coupons = [interest_rate]
        schedule = ql.sinkingSchedule(issue_date, maturity, frequency, calendar)
        notionals = ql.sinkingNotionals(maturity, frequency, interest_rate, face_value)

        amortizing_loan = ql.AmortizingFixedRateBond(
            settlement_days,
            notionals,
            schedule,
            coupons,
            day_count,
            business_convention,
            issue_date,
        )

        return amortizing_loan

    def amortizing_loan_payment_schedule(self, loan: ql.AmortizingFixedRateBond):

        interest_pmt = []
        principal_pmt = []
        outstanding = []
        last_outstanding = loan.notional(loan.issueDate())
        for i, cf in enumerate(loan.cashflows()):
            if i % 2 == 0:
                interest_pmt.append((cf.date(), cf.amount()))
            else:
                principal_pmt.append((cf.date(), cf.amount()))
                outstanding.append((cf.date(), last_outstanding - cf.amount()))
                _, last_outstanding = outstanding[-1]

        return interest_pmt, principal_pmt, outstanding
