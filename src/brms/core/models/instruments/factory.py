"""Factory helpers for creating instrument instances with sensible defaults."""

import datetime

import QuantLib as ql  # noqa: N813

from brms.core.models.instruments.base import BookType, CreditRating, InstrumentClass, Issuer, IssuerType
from brms.core.models.instruments.bonds import FixedRateBond, TreasuryNote
from brms.core.models.instruments.deposits import Deposit
from brms.core.models.instruments.equity import CommonEquity
from brms.core.models.instruments.loans import ResidentialMortgage


class InstrumentFactory:
    """Convenience factory for constructing common instruments."""

    @staticmethod
    def create_common_equity() -> CommonEquity:
        """Create a CommonEquity instrument."""
        return CommonEquity()

    @staticmethod
    def create_deposit() -> Deposit:
        """Create a Deposit instrument."""
        return Deposit()

    @staticmethod
    def create_treasury_note(  # noqa: PLR0913
        *,
        face_value: float,
        coupon_rate: float,
        issue_date: datetime.date,
        maturity_date: datetime.date,
        instrument_class: InstrumentClass,
        book_type: BookType = BookType.BANKING,
    ) -> TreasuryNote:
        """Create a TreasuryNote instrument."""
        issue_date_ql = ql.Date(issue_date.day, issue_date.month, issue_date.year)
        maturity_date_ql = ql.Date(maturity_date.day, maturity_date.month, maturity_date.year)
        return TreasuryNote(
            face_value=face_value,
            coupon_rate=coupon_rate,
            issue_date=issue_date_ql,
            maturity_date=maturity_date_ql,
            book_type=book_type,
            instrument_class=instrument_class,
            credit_rating=CreditRating.AAA,
            issuer=Issuer(
                name="Government",
                issuer_type=IssuerType.SOVEREIGN,
                credit_rating=CreditRating.AAA,
            ),
        )

    @staticmethod
    def create_residential_mortgage(  # noqa: PLR0913
        *,
        face_value: float,
        interest_rate: float,
        issue_date: datetime.date,
        maturity_years: int,
        frequency: ql.Period = ql.Monthly,
        settlement_days: int = 0,
        calendar: ql.Calendar = ql.NullCalendar(),  # noqa: B008
        day_count: ql.DayCounter = ql.ActualActual(ql.ActualActual.Actual365),  # noqa: B008
        business_convention: int = ql.Unadjusted,
        book_type: BookType = BookType.BANKING,
        credit_rating: CreditRating = CreditRating.UNRATED,
        issuer: Issuer | None = None,
        instrument_class: InstrumentClass = InstrumentClass.LOAN_AND_MORTGAGE,
    ) -> ResidentialMortgage:
        """Create a ResidentialMortgage instrument."""
        issue_date_ql = ql.Date(issue_date.day, issue_date.month, issue_date.year)
        maturity: ql.Period = ql.Period(maturity_years, ql.Years)
        if issuer is None:
            issuer = Issuer(
                name="Residential Mortgage Issuer",
                issuer_type=IssuerType.INDIVIDUAL,
                credit_rating=CreditRating.UNRATED,
            )
        return ResidentialMortgage(
            face_value=face_value,
            interest_rate=interest_rate,
            issue_date=issue_date_ql,
            maturity=maturity,
            frequency=frequency,
            settlement_days=settlement_days,
            calendar=calendar,
            day_count=day_count,
            business_convention=business_convention,
            book_type=book_type,
            credit_rating=credit_rating,
            issuer=issuer,
            instrument_class=instrument_class,
        )

    @staticmethod
    def create_fixed_rate_bond(  # noqa: PLR0913
        *,
        face_value: float,
        coupon_rate: float,
        issue_date: datetime.date,
        maturity_date: datetime.date,
        frequency: ql.Period = ql.Annual,
        settlement_days: int = 0,
        calendar: ql.Calendar = ql.NullCalendar(),  # noqa: B008
        day_count: ql.DayCounter = ql.ActualActual(ql.ActualActual.Actual365),  # noqa: B008
        business_convention: int = ql.Unadjusted,
        date_generation: ql.DateGeneration = ql.DateGeneration.Backward,
        month_end: bool = False,
        book_type: BookType = BookType.BANKING,
        credit_rating: CreditRating = CreditRating.UNRATED,
        issuer: Issuer | None = None,
        instrument_class: InstrumentClass = InstrumentClass.HTM,
    ) -> FixedRateBond:
        """Create a FixedRateBond instrument."""
        issue_date_ql = ql.Date(issue_date.day, issue_date.month, issue_date.year)
        maturity_date_ql = ql.Date(maturity_date.day, maturity_date.month, maturity_date.year)
        if issuer is None:
            issuer = Issuer(
                name="Bond Issuer",
                issuer_type=IssuerType.CORPORATE,
                credit_rating=CreditRating.UNRATED,
            )
        return FixedRateBond(
            face_value=face_value,
            coupon_rate=coupon_rate,
            issue_date=issue_date_ql,
            maturity_date=maturity_date_ql,
            frequency=frequency,
            settlement_days=settlement_days,
            calendar=calendar,
            day_count=day_count,
            business_convention=business_convention,
            date_generation=date_generation,
            month_end=month_end,
            book_type=book_type,
            instrument_class=instrument_class,
            credit_rating=credit_rating,
            issuer=issuer,
        )
