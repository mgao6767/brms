"""Bond instrument classes for the core domain model."""

import datetime
from functools import cache
from typing import TYPE_CHECKING, Optional

import QuantLib as ql  # noqa: N813

from brms.core.enums import InstrumentType
from brms.core.models.instruments.base import Instrument, InstrumentClass
from brms.core.utils import pydate_to_qldate, qldate_to_pydate, qldate_to_string

if TYPE_CHECKING:
    from brms.core.models.instruments.base import BookType, CreditRating, Issuer


class FixedRateBond(Instrument):
    """A class representing a fixed rate bond."""

    _instrument_type_label = "Fixed Rate Bond"
    _instrument_type_enum = InstrumentType.FIXED_RATE_BOND

    def __init__(  # noqa: PLR0913
        self,
        *,
        face_value: float,
        coupon_rate: float,
        issue_date: ql.Date,
        maturity_date: ql.Date,
        frequency: ql.Period = ql.Semiannual,
        settlement_days: int = 0,
        calendar: ql.Calendar = ql.NullCalendar(),  # noqa: B008
        day_count: ql.DayCounter = ql.Thirty360(ql.Thirty360.BondBasis),  # noqa: B008
        business_convention: int = ql.Unadjusted,
        date_generation: ql.DateGeneration = ql.DateGeneration.Backward,
        month_end: bool = False,
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
            business_convention (int, optional): The business convention. Defaults to ql.Unadjusted.
            date_generation (ql.DateGeneration, optional): The date generation rule for coupon dates.
                Defaults to ql.DateGeneration.Backward.
            month_end (bool, optional): Whether the coupon dates should be adjusted to the end of the month.
                Defaults to False.
            book_type (BookType, optional): The book type of the instrument.
            credit_rating (CreditRating, optional): The credit rating of the instrument.
            issuer (Issuer, optional): The issuer of the instrument.
            parent (Instrument, optional): The parent instrument.
            instrument_class (InstrumentClass, optional): The instrument class.

        """
        maturity_date_str = qldate_to_string(maturity_date)
        name = f"{coupon_rate * 100:.2f}% {maturity_date_str} {self._instrument_type_label}"
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
        self.instrument_type = self._instrument_type_enum
        self.ql_instrument = self.instrument

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
        """Get the maturity date of the bond."""
        return qldate_to_pydate(self.instrument.maturityDate())

    @property
    def issue_date(self) -> datetime.date:
        """Get the issue date of the bond."""
        return qldate_to_pydate(self.instrument.issueDate())

    def accept(self, visitor: object) -> None:
        """Accept a visitor."""
        visitor.visit_fixed_rate_bond(self)  # type: ignore[union-attr]

    def set_pricing_engine(self, engine: ql.PricingEngine) -> None:
        """Set the pricing engine."""
        self.instrument.setPricingEngine(engine)

    @cache  # noqa: B019
    def payment_schedule(self) -> list[tuple[datetime.date, float]]:
        """Generate the payment schedule for the bond.

        Returns:
            list: A list of tuples representing the payment schedule. Each tuple contains the payment date and amount.

        """
        return [(qldate_to_pydate(cf.date()), cf.amount()) for cf in self.instrument.cashflows()]


class TreasuryNote(FixedRateBond):
    """Represents a Treasury Note with a fixed interest rate and maturity between one and ten years."""

    _instrument_type_label = "Treasury Note"
    _instrument_type_enum = InstrumentType.TREASURY_NOTE


class TreasuryBond(FixedRateBond):
    """Represents a Treasury Bond with a fixed interest rate and maturity greater than ten years."""

    _instrument_type_label = "Treasury Bond"
    _instrument_type_enum = InstrumentType.TREASURY_BOND


class CoveredBond(Instrument):
    """A class to represent covered bond instruments."""

    def __init__(self, **kwargs: object) -> None:
        """Initialize a covered bond."""
        super().__init__(**kwargs)  # type: ignore[arg-type]
        self.instrument_type = InstrumentType.COVERED_BOND

    def accept(self, visitor: object) -> None:
        """Accept a visitor."""
        visitor.visit_covered_bond(self)  # type: ignore[union-attr]
