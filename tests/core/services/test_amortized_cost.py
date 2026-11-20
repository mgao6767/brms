"""AmortizedCostCalculator: effective interest rate and amortised cost of a position."""
# ruff: noqa: D103

from __future__ import annotations

import datetime
import itertools
from decimal import Decimal

import pytest
import QuantLib as ql  # noqa: N813

from brms.core.enums import MeasurementBasis
from brms.core.models.instruments.loans import ResidentialMortgage
from brms.core.rules.interest_accrual import scaled_accrued_amount
from brms.core.services.amortized_cost import AmortizedCostCalculator
from brms.core.utils import pydate_to_qldate
from tests.support.engine import R_FACE, make_bond, make_position

_CENT = Decimal("0.01")
_FACE = Decimal(str(R_FACE))
_COUPON_DATES = (datetime.date(2021, 7, 1), datetime.date(2022, 1, 3))  # bond R, as adjusted
_MATURITY = datetime.date(2022, 7, 1)


def _accrued(bond, day: datetime.date) -> Decimal:  # noqa: ANN001
    return scaled_accrued_amount(bond.ql_instrument, pydate_to_qldate(day))


def _position(bond, acquired: datetime.date, clean: Decimal, pid: str = "pos-R"):  # noqa: ANN001, ANN202
    return make_position(
        id=pid, instrument_id=bond.id, basis=MeasurementBasis.AMORTIZED_COST,
        acquired=acquired, cost=clean + _accrued(bond, acquired),
    )


def _days(start: datetime.date, end: datetime.date) -> list[datetime.date]:
    return [start + datetime.timedelta(days=i) for i in range((end - start).days + 1)]


def test_amortized_cost_starts_at_clean_cost() -> None:
    bond = make_bond(id="R")
    acquired = datetime.date(2021, 3, 15)
    pos = _position(bond, acquired, Decimal(510_000))
    assert abs(AmortizedCostCalculator().amortized_cost(bond, pos, acquired) - Decimal(510_000)) <= _CENT  # noqa: S101


@pytest.mark.parametrize("clean", [Decimal(520_000), Decimal(480_000)])
def test_amortized_cost_reaches_face_at_maturity(clean: Decimal) -> None:
    bond = make_bond(id="R")
    pos = _position(bond, datetime.date(2021, 1, 4), clean)
    calc = AmortizedCostCalculator()
    for day in (_MATURITY, _MATURITY + datetime.timedelta(days=10)):
        assert calc.amortized_cost(bond, pos, day) == _FACE  # noqa: S101


def test_premium_amortizes_monotonically_on_coupon_dates() -> None:
    bond = make_bond(id="R")
    pos = _position(bond, datetime.date(2021, 1, 4), Decimal(520_000))
    calc = AmortizedCostCalculator()
    values = [Decimal(520_000)] + [calc.amortized_cost(bond, pos, d) for d in (*_COUPON_DATES, _MATURITY)]
    assert all(a > b for a, b in itertools.pairwise(values)), values  # noqa: S101


def test_dirty_amortized_cost_is_pv_at_effective_rate() -> None:
    bond = make_bond(id="R")
    pos = _position(bond, datetime.date(2021, 1, 4), Decimal(520_000))
    calc = AmortizedCostCalculator()
    rate = ql.InterestRate(calc.effective_rate(bond, pos), bond.ql_instrument.dayCounter(), ql.Compounded, 2)
    for day in (datetime.date(2021, 2, 10), datetime.date(2021, 5, 22), datetime.date(2021, 10, 3)):
        qd = pydate_to_qldate(day)
        expected = Decimal(str(ql.CashFlows.npv(bond.ql_instrument.cashflows(), rate, False, qd, qd)))  # noqa: FBT003
        actual = calc.amortized_cost(bond, pos, day) + _accrued(bond, day)
        assert abs(actual - expected) <= _CENT, (day, actual, expected)  # noqa: S101


def test_par_bond_is_at_face_on_coupon_dates_and_close_between() -> None:
    """A par bond with regular coupon periods stays at face on coupon dates.

    Bond R is not used here: its January coupon date is adjusted to 4 January, so its periods
    are irregular and a par purchase does not stay exactly at par. This bond's coupon dates are
    all business days, so every 30/360 period is exactly half a year.
    """
    coupon_dates = (datetime.date(2021, 9, 15), datetime.date(2022, 3, 15))
    maturity = datetime.date(2022, 9, 15)
    bond = make_bond(id="P", issue=datetime.date(2020, 9, 15), maturity=maturity)
    acquired = datetime.date(2021, 3, 15)
    pos = _position(bond, acquired, _FACE)
    calc = AmortizedCostCalculator()
    for day in _days(acquired, maturity):
        value = calc.amortized_cost(bond, pos, day)
        if day in coupon_dates or day in (acquired, maturity):
            assert abs(value - _FACE) <= _CENT, (day, value)  # noqa: S101
        else:
            assert abs(value - _FACE) <= 100, (day, value)  # noqa: S101, PLR2004


def test_bond_bought_in_final_coupon_period() -> None:
    bond = make_bond(id="R")
    acquired = datetime.date(2022, 3, 15)
    pos = _position(bond, acquired, Decimal(501_000))
    calc = AmortizedCostCalculator()
    calc.effective_rate(bond, pos)
    assert abs(calc.amortized_cost(bond, pos, acquired) - Decimal(501_000)) <= _CENT  # noqa: S101
    assert calc.amortized_cost(bond, pos, _MATURITY) == _FACE  # noqa: S101


def test_loan_amortized_cost_is_cost_less_scheduled_principal() -> None:
    loan = ResidentialMortgage(
        face_value=300_000.0, interest_rate=0.06, issue_date=ql.Date(15, 12, 2020), maturity=ql.Period(1, ql.Years),
    )
    loan.id = "M"
    acquired = datetime.date(2021, 1, 20)
    _interest, principal, _outstanding = loan.payment_schedule()
    outstanding = Decimal(str(loan.face_value)) - sum(Decimal(str(a)) for d, a in principal if d <= acquired)
    pos = make_position(
        id="pos-M", instrument_id="M", basis=MeasurementBasis.AMORTIZED_COST,
        acquired=acquired, cost=outstanding + _accrued(loan, acquired),
    )
    day = datetime.date(2021, 4, 20)
    repaid = sum(Decimal(str(a)) for d, a in principal if acquired < d <= day)
    assert abs(AmortizedCostCalculator().amortized_cost(loan, pos, day) - (outstanding - repaid)) <= _CENT  # noqa: S101


def test_effective_rate_is_memoised_per_instance_not_globally() -> None:
    bond = make_bond(id="R")
    acquired = datetime.date(2021, 1, 4)
    premium = _position(bond, acquired, Decimal(520_000), pid="same-id")
    discount = _position(bond, acquired, Decimal(480_000), pid="same-id")
    first, second = AmortizedCostCalculator(), AmortizedCostCalculator()
    assert first.effective_rate(bond, premium) < second.effective_rate(bond, discount)  # noqa: S101
    assert first.effective_rate(bond, discount) == first.effective_rate(bond, premium)  # noqa: S101
