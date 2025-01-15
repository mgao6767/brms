import datetime

import QuantLib as ql

from brms.instruments.base import Instrument
from brms.instruments.visitor import Visitor
from brms.utils import pydate_to_qldate, qldate_to_string


class AmortizingFixedRateLoan(Instrument):
    """A class representing an amortizing fixed rate loan."""

    # TODO: book_type, etc. for Instrument's init
    def __init__(
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
    ):
        """Build a fixed rate amortizing loan object.

        Args:
            face_value (float): The face value of the instrument.
            interest_rate (float): The interest rate of the instrument.
            issue_date (ql.Date): The issue date of the instrument.
            maturity (ql.Period): The maturity period of the instrument.
            frequency (ql.Period, optional): The frequency of coupon payments. Defaults to ql.Semiannual.
            settlement_days (int, optional): The number of settlement days. Defaults to 0.
            calendar (ql.Calendar, optional): The calendar used for date calculations. Defaults to ql.NullCalendar().
            day_count (ql.DayCounter, optional): The day count convention used for interest calculations. Defaults to ql.Thirty360(ql.Thirty360.BondBasis).
            business_convention (int, optional): The business convention used for date adjustments. Defaults to ql.Unadjusted.
        """
        maturity_date_str = qldate_to_string(issue_date + maturity)
        name = f"{interest_rate*100:.2f}% {maturity_date_str}"
        super().__init__(name)

        coupons = [interest_rate]
        schedule = ql.sinkingSchedule(issue_date, maturity, frequency, calendar)
        notionals = ql.sinkingNotionals(maturity, frequency, interest_rate, face_value)

        self.instrument = ql.AmortizingFixedRateBond(
            settlement_days,
            notionals,
            schedule,
            coupons,
            day_count,
            business_convention,
            issue_date,
        )

    def notional(self, date: datetime.date) -> float:
        """Calculate the notional value of the loan on a given date.

        Args:
            date (datetime.date): The date for which to calculate the notional value.

        Returns:
            float: The notional value of the bond on the given date.

        """
        return self.instrument.notional(pydate_to_qldate(date))

    def accept(self, visitor: Visitor) -> None:
        """Accept a visitor."""
        visitor.visit_amortizing_fixed_rate_loan(self)

    def set_pricing_engine(self, engine: ql.PricingEngine) -> None:
        """Set the pricing engine."""
        self.instrument.setPricingEngine(engine)
