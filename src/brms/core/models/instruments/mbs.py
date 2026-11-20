"""Agency mortgage pass-through securities with a rate-dependent prepayment model.

A pass-through pays its holders, each month, interest at the pass-through ``coupon_rate`` on the
pool balance plus all principal the borrowers repay: the scheduled principal of a level-payment
mortgage at the pool's note rate (``wac``), re-amortised every month over the remaining term, and
prepayments. Prepayments are a share SMM = 1 - (1 - CPR)^(1/12) of the balance left after
scheduled principal.

Two speeds are used (a deliberate simplification):

* **Realised paydowns** follow a constant ``pricing_cpr`` fixed when the pool is set up. The
  security is a QuantLib amortising fixed-rate bond with those notionals, so interest accrual,
  settlement, principal paydowns and the ledger work exactly as for amortising loans.
* **Valuation** re-projects the remaining cash flows from the current balance at the CPR the
  :class:`PrepaymentModel` gives for today's curve (:meth:`MortgageBackedSecurity.projected_leg`).
  Rising rates slow prepayments and lengthen the pool (extension); falling rates speed them up
  and cap price gains (negative convexity). Fair value, spread calibration and EVE use it.

So realised cash flows do not respond to rates; only values do.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, fields
from functools import cache
from typing import TYPE_CHECKING

import QuantLib as ql  # noqa: N813

from brms.core.enums import InstrumentType
from brms.core.models.instruments.base import Instrument
from brms.core.rules.amortization import AmortizationRule
from brms.core.rules.interest_accrual import InterestIncomeAccrualRule
from brms.core.rules.loan_interest_settlement import LoanInterestSettlementRule
from brms.core.rules.mark_to_market import MarkToMarketRule
from brms.core.rules.sale import SaleRule
from brms.core.utils import pydate_to_qldate, qldate_to_pydate, qldate_to_string

if TYPE_CHECKING:
    import datetime

    from brms.core.models.instruments.base import BookType, CreditRating, Issuer, MeasurementBasis
    from brms.core.visitors.base import Visitor

_MONTHS_PER_YEAR = 12
_RATE_TENOR = ql.Period(10, ql.Years)


@dataclass(frozen=True)
class PrepaymentModel:
    """Annual prepayment speed (CPR) as an S-curve in the refinancing incentive.

    ``incentive = wac - mortgage rate``, with the mortgage rate taken as the curve's 10-year zero
    rate (semi-annual) plus ``mortgage_spread``. The CPR rises from ``turnover_cpr`` (housing
    turnover, no refinancing) to ``max_cpr``, reaching the midpoint at ``refi_center``; ``refi_width``
    sets how quickly.
    """

    turnover_cpr: float = 0.06
    max_cpr: float = 0.50
    refi_center: float = 0.0075
    refi_width: float = 0.0075
    mortgage_spread: float = 0.017

    def cpr(self, incentive: float) -> float:
        """Return the annual prepayment rate for *incentive* (decimal)."""
        z = (incentive - self.refi_center) / self.refi_width
        return self.turnover_cpr + (self.max_cpr - self.turnover_cpr) / (1 + math.exp(-z))

    @classmethod
    def from_value(cls, value: PrepaymentModel | dict[str, float] | None) -> PrepaymentModel:
        """Build from a model, a JSON object of its fields, or None (defaults)."""
        if value is None:
            return cls()
        if isinstance(value, PrepaymentModel):
            return value
        unknown = set(value) - {f.name for f in fields(cls)}
        if unknown:
            msg = f"Unknown prepayment model fields: {sorted(unknown)}"
            raise ValueError(msg)
        return cls(**{k: float(v) for k, v in value.items()})


def _smm(cpr: float) -> float:
    return 1 - (1 - cpr) ** (1 / _MONTHS_PER_YEAR)


def _paydowns(balance: float, wac: float, months: int, cpr: float) -> list[tuple[float, float]]:
    """Return ``(balance at the start of the month, principal paid at its end)`` for each month."""
    r = wac / _MONTHS_PER_YEAR
    smm = _smm(cpr)
    out = []
    for k in range(months):
        remaining = months - k
        if remaining == 1:
            paid = balance
        else:
            scheduled = balance / remaining if r == 0 else balance * r / (1 - (1 + r) ** -remaining)
            scheduled -= balance * r
            paid = scheduled + smm * (balance - scheduled)
        out.append((balance, paid))
        balance -= paid
    return out


class MortgageBackedSecurity(Instrument):
    """An agency mortgage pass-through security (monthly, 30/360, no payment delay)."""

    applicable_rules = frozenset({
        InterestIncomeAccrualRule, LoanInterestSettlementRule, AmortizationRule, MarkToMarketRule, SaleRule,
    })

    def __init__(  # noqa: PLR0913
        self,
        *,
        face_value: float,
        coupon_rate: float,
        issue_date: ql.Date,
        maturity: ql.Period,
        wac: float | None = None,
        pricing_cpr: float | None = None,
        prepayment: PrepaymentModel | dict[str, float] | None = None,
        book_type: BookType | None = None,
        credit_rating: CreditRating | None = None,
        issuer: Issuer | None = None,
        parent: Instrument | None = None,
        measurement_basis: MeasurementBasis | None = None,
    ) -> None:
        """Build a pass-through.

        Args:
            face_value: Pool balance on the issue date.
            coupon_rate: Pass-through rate paid to holders.
            issue_date: Date the pool starts (or the date it is described as of); payments fall on
                the same day of each later month.
            maturity: Remaining term of the pool's mortgages.
            wac: Weighted-average note rate of the mortgages (default: coupon + 0.50%).
            pricing_cpr: Constant speed of the realised paydowns (default: the model's CPR at zero
                refinancing incentive).
            prepayment: The prepayment model used for valuation (defaults if omitted).
            book_type: The book type of the instrument.
            credit_rating: The issue's credit rating.
            issuer: The issuer or guarantor.
            parent: The parent instrument.
            measurement_basis: The instrument class.

        """
        self.prepayment = PrepaymentModel.from_value(prepayment)
        self.coupon_rate = float(coupon_rate)
        self.wac = self.coupon_rate + 0.005 if wac is None else float(wac)
        self.pricing_cpr = self.prepayment.cpr(0.0) if pricing_cpr is None else float(pricing_cpr)
        maturity_date = issue_date + maturity
        name = f"{self.coupon_rate * 100:.2f}% {qldate_to_string(maturity_date)} MBS"
        super().__init__(name, book_type, credit_rating, issuer, parent, measurement_basis=measurement_basis)
        self.instrument_type = InstrumentType.MORTGAGE_BACKED_SECURITY
        self._face_value = float(face_value)

        self._schedule = ql.Schedule(
            issue_date, maturity_date, ql.Period(ql.Monthly), ql.NullCalendar(), ql.Unadjusted, ql.Unadjusted,
            ql.DateGeneration.Forward, False,  # noqa: FBT003
        )
        months = len(self._schedule) - 1
        notionals = [b for b, _paid in _paydowns(self._face_value, self.wac, months, self.pricing_cpr)]
        self.instrument = ql.AmortizingFixedRateBond(
            0, notionals, self._schedule, [self.coupon_rate], ql.Thirty360(ql.Thirty360.BondBasis), ql.Unadjusted,
            issue_date,
        )
        self.ql_instrument = self.instrument

    @property
    def face_value(self) -> float:
        """Pool balance on the issue date."""
        return self._face_value

    @property
    def issue_date(self) -> datetime.date:
        """Issue date of the pool."""
        return qldate_to_pydate(self.instrument.issueDate())

    @property
    def maturity_date(self) -> datetime.date:
        """Last scheduled payment date."""
        return qldate_to_pydate(self.instrument.maturityDate())

    def notional(self, date: datetime.date) -> float:
        """Balance of the coupon period containing *date*."""
        return self.instrument.notional(pydate_to_qldate(date))

    @cache  # noqa: B019
    def payment_schedule(
        self,
    ) -> tuple[list[tuple[datetime.date, float]], list[tuple[datetime.date, float]], list[tuple[datetime.date, float]]]:
        """Return the realised (pricing-speed) interest, principal and outstanding schedules."""
        interest, principal, outstanding = [], [], []
        running = self._face_value
        for cf in self.instrument.cashflows():
            day = qldate_to_pydate(cf.date())
            if ql.as_coupon(cf) is not None:
                interest.append((day, cf.amount()))
            else:
                principal.append((day, cf.amount()))
                running -= cf.amount()
                outstanding.append((day, running))
        return interest, principal, outstanding

    def outstanding(self, date: datetime.date) -> float:
        """Balance at close of business on *date* (after any payment that day)."""
        _interest, principal, _outstanding = self.payment_schedule()
        return self._face_value - sum(a for d, a in principal if d <= date)

    def mortgage_rate(self, curve: ql.YieldTermStructureHandle, date: datetime.date) -> float:
        """Primary mortgage rate implied by *curve*: its 10-year zero rate plus the mortgage spread."""
        tenor_date = pydate_to_qldate(date) + _RATE_TENOR
        zero = curve.zeroRate(tenor_date, ql.Actual365Fixed(), ql.Compounded, ql.Semiannual).rate()
        return zero + self.prepayment.mortgage_spread

    def speed(self, curve: ql.YieldTermStructureHandle, date: datetime.date) -> float:
        """CPR the prepayment model gives on *date* for *curve*."""
        return self.prepayment.cpr(self.wac - self.mortgage_rate(curve, date))

    def projected_leg(self, curve: ql.YieldTermStructureHandle, date: datetime.date) -> list[ql.CashFlow]:
        """Return the expected cash flows after *date*, from the current balance at the speed *curve* implies."""
        future = [d for d in self._schedule if qldate_to_pydate(d) > date]
        balance = self.outstanding(date)
        if not future or balance <= 0:
            return []
        monthly_coupon = self.coupon_rate / _MONTHS_PER_YEAR
        flows = _paydowns(balance, self.wac, len(future), self.speed(curve, date))
        return [
            ql.SimpleCashFlow(start * monthly_coupon + paid, day)
            for day, (start, paid) in zip(future, flows, strict=True)
        ]

    def set_pricing_engine(self, engine: ql.PricingEngine) -> None:
        """Set the pricing engine."""
        self.instrument.setPricingEngine(engine)

    def accept(self, visitor: Visitor) -> None:
        """Accept a visitor (shown as an amortising fixed-rate instrument)."""
        visitor.visit_amortizing_fixed_rate_loan(self)  # type: ignore[arg-type]
