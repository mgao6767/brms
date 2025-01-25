import datetime

import QuantLib as ql

from brms.instruments.base import CreditRating, InstrumentClass, Issuer, IssuerType
from brms.instruments.common_equity import CommonEquity
from brms.instruments.deposit import Deposit
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
    ) -> TreasuryNote:
        issue_date_ql = ql.Date(issue_date.day, issue_date.month, issue_date.year)
        maturity_date_ql = ql.Date(maturity_date.day, maturity_date.month, maturity_date.year)
        return TreasuryNote(
            face_value=face_value,
            coupon_rate=coupon_rate,
            issue_date=issue_date_ql,
            maturity_date=maturity_date_ql,
            book_type=BookType.BANKING_BOOK,
            instrument_class=instrument_class,
            credit_rating=CreditRating.AAA,
            issuer=Issuer(
                name="Government",
                issuer_type=IssuerType.SOVEREIGN,
                credit_rating=CreditRating.AAA,
            ),
        )
