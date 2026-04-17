"""Loan instrument classes for the core domain model."""

from __future__ import annotations

import datetime
from functools import cache
from typing import TYPE_CHECKING

import QuantLib as ql  # noqa: N813

from brms.core.enums import InstrumentType
from brms.core.models.benchmarks import BenchmarkFamily, PrincipalRepaymentMode
from brms.core.models.instruments.base import Instrument, MeasurementBasis
from brms.core.rules.amortization import AmortizationRule
from brms.core.rules.interest_accrual import InterestIncomeAccrualRule
from brms.core.rules.loan_interest_settlement import LoanInterestSettlementRule
from brms.core.utils import pydate_to_qldate, qldate_to_pydate, qldate_to_string

if TYPE_CHECKING:
    from brms.core.models.instruments.base import BookType, CreditRating, Issuer
    from brms.core.visitors.base import Visitor


class AmortizingFixedRateLoan(Instrument):
    """A class representing an amortizing fixed rate loan."""

    applicable_rules = frozenset({InterestIncomeAccrualRule, LoanInterestSettlementRule, AmortizationRule})
    _instrument_type_label = "Amortizing Fixed Rate Loan"
    _instrument_type_enum = InstrumentType.AMORTIZING_FIXED_RATE_LOAN

    def __init__(  # noqa: PLR0913
        self,
        face_value: float,
        interest_rate: float,
        issue_date: ql.Date,
        maturity: ql.Period,
        frequency: ql.Period = ql.Semiannual,
        settlement_days: int = 0,
        calendar: ql.Calendar = ql.NullCalendar(),  # noqa: B008
        day_count: ql.DayCounter = ql.Thirty360(ql.Thirty360.BondBasis),  # noqa: B008
        business_convention: int = ql.Unadjusted,
        book_type: BookType | None = None,
        credit_rating: CreditRating | None = None,
        issuer: Issuer | None = None,
        parent: Instrument | None = None,
        measurement_basis: MeasurementBasis | None = None,
    ) -> None:
        """Build a fixed rate amortizing loan object.

        Args:
            face_value (float): The face value of the instrument.
            interest_rate (float): The interest rate of the instrument.
            issue_date (ql.Date): The issue date of the instrument.
            maturity (ql.Period): The maturity period of the instrument.
            frequency (ql.Period, optional): The frequency of coupon payments. Defaults to ql.Semiannual.
            settlement_days (int, optional): The number of settlement days. Defaults to 0.
            calendar (ql.Calendar, optional): The calendar used for date calculations. Defaults to ql.NullCalendar().
            day_count (ql.DayCounter, optional): The day count convention used for interest calculations.
                Defaults to ql.Thirty360(ql.Thirty360.BondBasis).
            business_convention (int, optional): The business convention used for date adjustments.
                Defaults to ql.Unadjusted.
            book_type (BookType, optional): The book type of the instrument.
            credit_rating (CreditRating, optional): The credit rating of the instrument.
            issuer (Issuer, optional): The issuer of the instrument.
            parent (Instrument, optional): The parent instrument.
            measurement_basis (MeasurementBasis, optional): The instrument class.

        """
        maturity_date_str = qldate_to_string(issue_date + maturity)
        name = f"{interest_rate * 100:.2f}% {maturity_date_str} {self._instrument_type_label}"
        super().__init__(name, book_type, credit_rating, issuer, parent, measurement_basis=measurement_basis)

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
        self.instrument_type = self._instrument_type_enum
        self.ql_instrument = self.instrument

    def notional(self, date: datetime.date) -> float:
        """Calculate the notional value of the loan on a given date.

        Args:
            date (datetime.date): The date for which to calculate the notional value.

        Returns:
            float: The notional value of the loan on the given date.

        """
        return self.instrument.notional(pydate_to_qldate(date))

    @property
    def maturity_date(self) -> datetime.date:
        """Get the maturity date of the loan."""
        return qldate_to_pydate(self.instrument.maturityDate())

    @property
    def issue_date(self) -> datetime.date:
        """Get the issue date of the loan."""
        return qldate_to_pydate(self.instrument.issueDate())

    @property
    def interest_rate(self) -> float:
        """Get the interest rate of the loan."""
        return self.instrument.nextCouponRate()

    @property
    def face_value(self) -> float:
        """Get the face value of the loan."""
        return self.instrument.notional(self.instrument.issueDate())

    def accept(self, visitor: Visitor) -> None:
        """Accept a visitor."""
        visitor.visit_amortizing_fixed_rate_loan(self)  # type: ignore[union-attr]

    def set_pricing_engine(self, engine: ql.PricingEngine) -> None:
        """Set the pricing engine."""
        self.instrument.setPricingEngine(engine)

    @cache  # noqa: B019
    def payment_schedule(
        self,
    ) -> tuple[list[tuple[datetime.date, float]], list[tuple[datetime.date, float]], list[tuple[datetime.date, float]]]:
        """Calculate the payment schedule for the instrument.

        Returns:
            Tuple: A tuple containing three lists:
                - interest_pmt: A list of tuples representing the date and amount of interest payments.
                - principal_pmt: A list of tuples representing the date and amount of principal payments.
                - outstanding: A list of tuples representing the date and outstanding balance after each payment.

        """
        loan = self.instrument
        interest_pmt = []
        principal_pmt = []
        outstanding = []
        last_outstanding = loan.notional(loan.issueDate())
        for i, cf in enumerate(loan.cashflows()):
            if i % 2 == 0:
                interest_pmt.append((qldate_to_pydate(cf.date()), cf.amount()))
            else:
                principal_pmt.append((qldate_to_pydate(cf.date()), cf.amount()))
                outstanding.append((qldate_to_pydate(cf.date()), last_outstanding - cf.amount()))
                _, last_outstanding = outstanding[-1]

        return (interest_pmt, principal_pmt, outstanding)


class Mortgage(AmortizingFixedRateLoan):
    """Base class for mortgages with a fixed interest rate.

    Defaults to monthly payments (``ql.Monthly``), overriding the base
    class semi-annual default.
    """

    _instrument_type_label = "Mortgage"
    _instrument_type_enum = InstrumentType.MORTGAGE
    _default_frequency = ql.Monthly

    def __init__(self, *, frequency: int = ql.Monthly, **kwargs: object) -> None:  # type: ignore[assignment]
        """Initialize a mortgage with monthly payment frequency by default."""
        super().__init__(frequency=frequency, **kwargs)  # type: ignore[arg-type]


class ResidentialMortgage(Mortgage):
    """Represents a residential mortgage with a fixed interest rate."""

    _instrument_type_label = "Residential Mortgage"
    _instrument_type_enum = InstrumentType.RESIDENTIAL_MORTGAGE


class CommercialMortgage(Mortgage):
    """Represents a commercial mortgage with a fixed interest rate."""

    _instrument_type_label = "Commercial Mortgage"
    _instrument_type_enum = InstrumentType.COMMERCIAL_MORTGAGE


class PersonalLoan(Instrument):
    """A class to represent personal loan instruments."""

    def __init__(self, **kwargs: object) -> None:
        """Initialize a personal loan."""
        super().__init__(**kwargs)  # type: ignore[arg-type]
        self.instrument_type = InstrumentType.PERSONAL_LOAN

    def accept(self, visitor: Visitor) -> None:
        """Accept a visitor."""
        visitor.visit_personal_loan(self)  # type: ignore[union-attr]


class CreditCard(Instrument):
    """A class to represent credit card instruments."""

    def __init__(self, **kwargs: object) -> None:
        """Initialize a credit card."""
        super().__init__(**kwargs)  # type: ignore[arg-type]
        self.instrument_type = InstrumentType.CREDIT_CARD

    def accept(self, visitor: Visitor) -> None:
        """Accept a visitor."""
        visitor.visit_credit_card(self)  # type: ignore[union-attr]


# ---------------------------------------------------------------------------
# Variable-rate loans
# ---------------------------------------------------------------------------


def _build_notionals(
    face_value: float,
    n_periods: int,
    mode: PrincipalRepaymentMode,
) -> list[float]:
    """Build notional schedule for each coupon period."""
    if mode == PrincipalRepaymentMode.BULLET:
        return [float(face_value)] * n_periods
    if mode == PrincipalRepaymentMode.SINKING:
        return [float(face_value) * (1.0 - i / n_periods) for i in range(n_periods)]
    msg = f"Unsupported principal_repayment_mode: {mode}"
    raise NotImplementedError(msg)


class VariableRateLoan(Instrument):
    """Benchmark-indexed variable-rate loan backed by ``ql.AmortizingFloatingRateBond``."""

    applicable_rules = frozenset({InterestIncomeAccrualRule, LoanInterestSettlementRule, AmortizationRule})
    _instrument_type_label = "Variable Rate Loan"

    def __init__(  # noqa: PLR0913
        self,
        face_value: float,
        spread: float,
        issue_date: ql.Date,
        maturity: ql.Period,
        ibor_index: ql.IborIndex,
        repricing_frequency: ql.Period | None = None,
        payment_frequency: ql.Period | None = None,
        principal_repayment_mode: PrincipalRepaymentMode = PrincipalRepaymentMode.BULLET,
        floor_rate: float | None = None,
        cap_rate: float | None = None,
        benchmark_family: BenchmarkFamily = BenchmarkFamily.PRIME,
        settlement_days: int = 0,
        calendar: ql.Calendar | None = None,
        day_count: ql.DayCounter | None = None,
        business_convention: int = ql.ModifiedFollowing,
        book_type: BookType | None = None,
        credit_rating: CreditRating | None = None,
        issuer: Issuer | None = None,
        parent: Instrument | None = None,
        measurement_basis: MeasurementBasis | None = MeasurementBasis.AMORTIZED_COST,
    ) -> None:
        """Build a variable-rate loan from contract terms and a shared IborIndex."""
        repricing_frequency = repricing_frequency or ql.Period(1, ql.Months)
        maturity_date_str = qldate_to_string(issue_date + maturity)
        name = f"Prime+{spread * 100:.0f}bp {maturity_date_str} {self._instrument_type_label}"
        super().__init__(
            name,
            book_type,
            credit_rating,
            issuer,
            parent,
            measurement_basis=measurement_basis,
            repricing_frequency=repricing_frequency,
        )
        self.instrument_type = InstrumentType.VARIABLE_RATE_LOAN
        self._face_value = float(face_value)
        self.spread = float(spread)
        self.floor_rate = floor_rate
        self.cap_rate = cap_rate
        self.benchmark_family = benchmark_family
        self.principal_repayment_mode = principal_repayment_mode
        self._issue_date = qldate_to_pydate(issue_date)
        self._maturity_date = qldate_to_pydate(issue_date + maturity)

        calendar = calendar or ql.UnitedStates(ql.UnitedStates.FederalReserve)
        day_count = day_count or ql.Actual365Fixed()
        payment_frequency = payment_frequency or repricing_frequency

        self._schedule = ql.Schedule(
            issue_date,
            issue_date + maturity,
            payment_frequency,
            calendar,
            business_convention,
            business_convention,
            ql.DateGeneration.Forward,
            False,  # noqa: FBT003
        )
        n_periods = len(list(self._schedule)) - 1
        notionals = _build_notionals(self._face_value, n_periods, principal_repayment_mode)

        self.instrument = ql.AmortizingFloatingRateBond(
            settlement_days,
            notionals,
            self._schedule,
            ibor_index,
            day_count,
            business_convention,
            0,
            [1.0] * n_periods,
            [float(spread)] * n_periods,
            [] if cap_rate is None else [float(cap_rate)] * n_periods,
            [] if floor_rate is None else [float(floor_rate)] * n_periods,
            False,  # noqa: FBT003
            issue_date,
        )
        self.ql_instrument = self.instrument

    @property
    def face_value(self) -> float:
        """Original face value of the loan."""
        return self._face_value

    @property
    def issue_date(self) -> datetime.date:
        """Issue date of the loan."""
        return self._issue_date

    @property
    def maturity_date(self) -> datetime.date:
        """Maturity date of the loan."""
        return self._maturity_date

    def notional(self, date: datetime.date) -> float:
        """Outstanding notional as of *date*."""
        return self.instrument.notional(pydate_to_qldate(date))

    def payment_schedule(
        self,
    ) -> tuple[list[tuple[datetime.date, float]], list[tuple[datetime.date, float]], list[tuple[datetime.date, float]]]:
        """Interest, principal, and outstanding schedules from QL cashflows.

        Interest amounts for future coupons may be unavailable if the index's
        forwarding curve is not yet linked; those coupons are skipped.
        Principal/redemption cashflows are always deterministic.
        """
        interest: list[tuple[datetime.date, float]] = []
        principal: list[tuple[datetime.date, float]] = []
        outstanding: list[tuple[datetime.date, float]] = []

        running = self._face_value
        for cf in self.instrument.cashflows():
            d = qldate_to_pydate(cf.date())
            coupon = ql.as_coupon(cf)
            if coupon is not None:
                try:
                    interest.append((d, cf.amount()))
                except RuntimeError:
                    pass
            else:
                amt = cf.amount()
                principal.append((d, amt))
                running -= amt
                outstanding.append((d, running))
        return interest, principal, outstanding

    def set_pricing_engine(self, engine: ql.PricingEngine) -> None:
        """Set the pricing engine for NPV calculations."""
        self.instrument.setPricingEngine(engine)

    def accept(self, visitor: Visitor) -> None:
        """Accept a visitor."""
        visitor.visit_variable_rate_loan(self)
