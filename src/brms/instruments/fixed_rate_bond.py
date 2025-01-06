import datetime

import QuantLib as ql

from brms.instruments.base import Instrument
from brms.instruments.valuation import ValuationVisitor
from brms.models.scenario import Scenario
from brms.utils import pydate_to_qldate, qldate_to_string


class FixedRateBond(Instrument):
    """A class representing a fixed rate bond."""

    def __init__(
        self,
        face_value: float,
        coupon_rate: float,
        issue_date: ql.Date,
        maturity_date: ql.Date,
        frequency: ql.Period = ql.Semiannual,
        settlement_days: int = 0,
        calendar: ql.Calendar = ql.NullCalendar(),
        day_count: ql.DayCounter = ql.Thirty360(ql.Thirty360.BondBasis),
        business_convention=ql.Unadjusted,
        date_generation: ql.DateGeneration = ql.DateGeneration.Backward,
        month_end=False,
    ) -> None:
        """Build a fixed rate bond object.

        Args:
            face_value (float): The face value of the bond.
            coupon_rate (float): The coupon rate of the bond.
            issue_date (ql.Date): The issue date of the bond.
            maturity_date (ql.Date): The maturity date of the bond.
            frequency (ql.Period, optional): The frequency of coupon payments. Defaults to ql.Semiannual.
            settlement_days (int, optional): The number of settlement days. Defaults to 0.
            calendar (ql.Calendar, optional): The calendar used for date calculations. Defaults to ql.NullCalendar().
            day_count (ql.DayCounter, optional): The day count convention for interest calculations.
                Defaults to ql.Thirty360(ql.Thirty360.BondBasis).
            business_convention (optional): The business convention. Defaults to ql.Unadjusted.
            date_generation (ql.DateGeneration, optional): The date generation rule for coupon dates.
            month_end (bool, optional): Whether the coupon dates should be adjusted to the end of the month.
                Defaults to False.
            date_generation (ql.DateGeneration, optional): The date generation rule for coupon dates.
                Defaults to ql.DateGeneration.Backward.
            month_end (bool, optional): Whether the coupon dates should be adjusted to the end of the month.
                Defaults to False.

        """
        maturity_date_str = qldate_to_string(maturity_date)
        name = f"{coupon_rate*100:.2f}% {maturity_date_str}"
        super().__init__(name)

        coupons = [coupon_rate]
        tenor = ql.Period(frequency)

        schedule = ql.Schedule(
            issue_date,
            maturity_date,
            tenor,
            calendar,
            business_convention,
            business_convention,
            date_generation,
            month_end,
        )

        self.instrument = ql.FixedRateBond(settlement_days, face_value, schedule, coupons, day_count)

    def notional(self, date: datetime.date) -> float:
        """Calculate the notional value of the bond on a given date.

        Args:
            date (datetime.date): The date for which to calculate the notional value.

        Returns:
            float: The notional value of the bond on the given date.

        """
        return self.instrument.notional(pydate_to_qldate(date))

    def accept(self, visitor: ValuationVisitor, scenario: Scenario) -> float:
        """Accept a valuation visitor to calculate the instrument's value."""
        return visitor.value_fixed_rate_bond(self, scenario)

    def set_pricing_engine(self, engine: ql.PricingEngine) -> None:
        """Set the pricing engine."""
        self.instrument.setPricingEngine(engine)
