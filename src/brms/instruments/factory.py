import datetime

import QuantLib as ql

from brms.instruments.base import CreditRating, InstrumentClass, Issuer, IssuerType
from brms.instruments.common_equity import CommonEquity
from brms.instruments.deposit import Deposit
from brms.instruments.fixed_rate_bond import FixedRateBond
from brms.instruments.mortgage import ResidentialMortgage
from brms.instruments.treasury_security import TreasuryNote
from brms.models.base import BookType


class InstrumentFactory:
    @staticmethod
    def create_common_equity(*, value: float) -> CommonEquity:
        return CommonEquity(value=value)

    @staticmethod
    def create_deposit(*, value: float) -> Deposit:
        return Deposit(value=value)

    @staticmethod
    def create_treasury_note(
        *,
        face_value: float,
        coupon_rate: float,
        issue_date: datetime.date,
        maturity_date: datetime.date,
        instrument_class: InstrumentClass,
        book_type: BookType = BookType.BANKING_BOOK,
    ) -> TreasuryNote:
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
    def create_residential_mortgage(
        *,
        face_value: float,
        interest_rate: float,
        issue_date: datetime.date,
        maturity_years: int,
        frequency: ql.Period = ql.Monthly,
        settlement_days: int = 0,
        calendar: ql.Calendar = ql.NullCalendar(),
        day_count: ql.DayCounter = ql.ActualActual(ql.ActualActual.Actual365),
        business_convention=ql.Unadjusted,
        book_type: BookType = BookType.BANKING_BOOK,
        credit_rating: CreditRating = CreditRating.UNRATED,
        issuer: Issuer | None = None,
        instrument_class: InstrumentClass = InstrumentClass.LOAN_AND_MORTGAGE,
    ) -> ResidentialMortgage:
        issue_date_ql = ql.Date(issue_date.day, issue_date.month, issue_date.year)
        maturity: ql.Period = ql.Period(maturity_years, ql.Years)
        if issuer is None:
            issuer = Issuer(
                name="Residential Mortgage Issuer",
                issuer_type=IssuerType.INDIVIDUAL,
                credit_rating=CreditRating.UNRATED,
            )
        mortgage = ResidentialMortgage(
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
        # Set value to its face value
        mortgage.value = face_value
        return mortgage

    @staticmethod
    def create_fixed_rate_bond(
        *,
        face_value: float,
        coupon_rate: float,
        issue_date: datetime.date,
        maturity_date: datetime.date,
        frequency: ql.Period = ql.Annual,
        settlement_days: int = 0,
        calendar: ql.Calendar = ql.NullCalendar(),
        day_count: ql.DayCounter = ql.ActualActual(ql.ActualActual.Actual365),
        business_convention=ql.Unadjusted,
        date_generation: ql.DateGeneration = ql.DateGeneration.Backward,
        month_end: bool = False,
        book_type: BookType = BookType.BANKING_BOOK,
        credit_rating: CreditRating = CreditRating.UNRATED,
        issuer: Issuer | None = None,
        instrument_class: InstrumentClass = InstrumentClass.HTM,
    ) -> ql.FixedRateBond:
        issue_date_ql = ql.Date(issue_date.day, issue_date.month, issue_date.year)
        maturity_date_ql = ql.Date(maturity_date.day, maturity_date.month, maturity_date.year)
        if issuer is None:
            issuer = Issuer(
                name="Bond Issuer",
                issuer_type=IssuerType.CORPORATE,
                credit_rating=CreditRating.UNRATED,
            )
        bond = FixedRateBond(
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
        return bond
