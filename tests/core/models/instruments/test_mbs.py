"""Agency pass-through MBS: scheduled paydowns at the pricing speed, projections at the market speed."""
# ruff: noqa: D103, S101, PLR2004

from __future__ import annotations

import datetime

import pytest
import QuantLib as ql  # noqa: N813

from brms.core.enums import InstrumentType
from brms.core.models.instruments import default_instrument_registry
from brms.core.models.instruments.mbs import MortgageBackedSecurity, PrepaymentModel
from brms.core.services.spreads import spreaded_handle
from brms.core.utils import pydate_to_qldate

_ISSUE = datetime.date(2021, 1, 15)


def _mbs(**kwargs) -> MortgageBackedSecurity:  # noqa: ANN003
    terms = {"face_value": 1_000_000.0, "coupon_rate": 0.02, "issue_date": pydate_to_qldate(_ISSUE),
             "maturity": ql.Period(30, ql.Years), "pricing_cpr": 0.08}
    return MortgageBackedSecurity(**{**terms, **kwargs})


def _flat(date: datetime.date, rate: float) -> ql.YieldTermStructureHandle:
    ql.Settings.instance().evaluationDate = pydate_to_qldate(date)
    curve = ql.FlatForward(pydate_to_qldate(date), rate, ql.Actual365Fixed(), ql.Compounded, ql.Semiannual)
    return ql.YieldTermStructureHandle(curve)


def test_s_curve() -> None:
    model = PrepaymentModel()
    assert model.cpr(model.refi_center) == pytest.approx((model.turnover_cpr + model.max_cpr) / 2)
    assert model.cpr(-0.08) == pytest.approx(model.turnover_cpr, abs=1e-3)
    assert model.cpr(0.08) == pytest.approx(model.max_cpr, abs=1e-3)
    assert model.cpr(0.0) < model.cpr(0.01)


def test_defaults_and_registry() -> None:
    mbs = default_instrument_registry().create(
        "mortgage_backed_security", face_value=100.0, coupon_rate=0.03, issue_date=pydate_to_qldate(_ISSUE),
        maturity=ql.Period(15, ql.Years), prepayment={"turnover_cpr": 0.05},
    )
    assert mbs.instrument_type == InstrumentType.MORTGAGE_BACKED_SECURITY
    assert mbs.wac == pytest.approx(0.035)
    assert mbs.prepayment.turnover_cpr == 0.05
    assert mbs.pricing_cpr == pytest.approx(mbs.prepayment.cpr(0.0))
    assert mbs.maturity_date == datetime.date(2036, 1, 15)


def test_first_paydown_is_scheduled_principal_plus_prepayment_at_the_pricing_speed() -> None:
    mbs = _mbs()
    _interest, principal, outstanding = mbs.payment_schedule()
    balance, r, n = 1_000_000.0, (0.02 + 0.005) / 12, 360
    scheduled = balance * r / (1 - (1 + r) ** -n) - balance * r
    smm = 1 - (1 - 0.08) ** (1 / 12)
    expected = scheduled + smm * (balance - scheduled)
    assert principal[0] == (datetime.date(2021, 2, 15), pytest.approx(expected, rel=1e-9))
    assert outstanding[-1][1] == pytest.approx(0.0, abs=1e-6)
    assert principal[-1][0] == mbs.maturity_date


def test_interest_is_coupon_on_the_period_balance() -> None:
    mbs = _mbs()
    interest, _principal, outstanding = mbs.payment_schedule()
    assert interest[0][1] == pytest.approx(1_000_000.0 * 0.02 / 12, rel=1e-9)
    assert interest[1][1] == pytest.approx(outstanding[0][1] * 0.02 / 12, rel=1e-9)


def test_projection_at_the_pricing_speed_reproduces_the_scheduled_flows() -> None:
    model = PrepaymentModel()
    mbs = _mbs(pricing_cpr=None)  # pricing speed = model speed at zero incentive
    day = datetime.date(2021, 6, 20)
    # A curve whose mortgage rate equals the WAC gives zero incentive.
    handle = _flat(day, mbs.wac - model.mortgage_spread)
    leg = mbs.projected_leg(handle, day)
    scheduled = [cf for cf in mbs.ql_instrument.cashflows() if cf.date() > pydate_to_qldate(day)]
    by_date: dict[ql.Date, float] = {}
    for cf in scheduled:
        by_date[cf.date()] = by_date.get(cf.date(), 0.0) + cf.amount()
    assert [cf.date() for cf in leg] == sorted(by_date)
    for cf in leg:
        assert cf.amount() == pytest.approx(by_date[cf.date()], rel=1e-6)


def test_higher_rates_slow_prepayment_and_extend_the_projection() -> None:
    mbs = _mbs()
    day = datetime.date(2021, 6, 20)

    def average_life(rate: float) -> float:
        leg = mbs.projected_leg(_flat(day, rate), day)
        coupon_free = [(cf.date(), cf.amount()) for cf in leg]
        total = sum(a for _d, a in coupon_free)
        return sum((d - pydate_to_qldate(day)) / 365 * a for d, a in coupon_free) / total

    assert mbs.speed(_flat(day, 0.005), day) > mbs.speed(_flat(day, 0.04), day)
    assert average_life(0.04) > average_life(0.005)


def test_pool_near_the_refinancing_threshold_shows_negative_convexity() -> None:
    mbs = _mbs(coupon_rate=0.03)
    day = datetime.date(2021, 6, 20)

    def price(rate: float) -> float:
        handle = _flat(day, rate)
        discount = spreaded_handle(handle, 0.008)
        return ql.CashFlows.npv(mbs.projected_leg(handle, day), discount, False, pydate_to_qldate(day))  # noqa: FBT003

    base, up, down = price(0.02), price(0.025), price(0.015)
    assert (down - base) < (base - up)  # gains from falling rates are smaller than losses from rising ones
