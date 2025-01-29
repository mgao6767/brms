import datetime
from functools import cache
from typing import TYPE_CHECKING, Optional

import QuantLib as ql

from brms.instruments.base import Instrument, InstrumentClass
from brms.utils import pydate_to_qldate, qldate_to_pydate, qldate_to_string

if TYPE_CHECKING:
    from brms.instruments.base import BookType, CreditRating, Issuer
    from brms.instruments.visitors import Visitor


class FixedRateBond(Instrument):
    """A class representing a fixed rate bond."""

    instrument_type = "Fixed Rate Bond"

    # TODO: book_type, etc. for Instrument's init
    def __init__(
        self,
        *,
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
        book_type: Optional["BookType"] = None,
        credit_rating: Optional["CreditRating"] = None,
        issuer: Optional["Issuer"] = None,
        parent: Optional["Instrument"] = None,
        instrument_class: Optional["InstrumentClass"] = None,
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
        name = f"{coupon_rate*100:.2f}% {maturity_date_str} {self.instrument_type}"
        super().__init__(name, book_type, credit_rating, issuer, parent, instrument_class=instrument_class)

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

        self.instrument = ql.FixedRateBond(
            settlement_days,
            face_value,
            schedule,
            coupons,
            day_count,
            ql.Following,
            100.0,
            issue_date,
        )

    def notional(self, date: datetime.date) -> float:
        """Calculate the notional value of the bond on a given date.

        Args:
            date (datetime.date): The date for which to calculate the notional value.

        Returns:
            float: The notional value of the bond on the given date.

        """
        return self.instrument.notional(pydate_to_qldate(date))

    @property
    def maturity_date(self) -> datetime.date:
        return qldate_to_pydate(self.instrument.maturityDate())

    @property
    def issue_date(self) -> datetime.date:
        return qldate_to_pydate(self.instrument.issueDate())

    def accept(self, visitor: "Visitor") -> None:
        """Accept a visitor."""
        visitor.visit_fixed_rate_bond(self)

    def set_pricing_engine(self, engine: ql.PricingEngine) -> None:
        """Set the pricing engine."""
        self.instrument.setPricingEngine(engine)

    @cache
    def payment_schedule(self):
        """
        Generates the payment schedule for a bond.

        Returns:
            list: A list of tuples representing the payment schedule. Each tuple contains the payment date and amount.
        """
        return [(qldate_to_pydate(cf.date()), cf.amount()) for cf in self.instrument.cashflows()]
