"""Tests for VariableRateLoan construction, schedule, and repricing hook."""

from __future__ import annotations

import datetime

import QuantLib as ql  # noqa: N813
import pytest

from brms.core.enums import InstrumentType
from brms.core.models.benchmarks import PrimeIndex, PrincipalRepaymentMode
from brms.core.models.instruments.loans import VariableRateLoan

_FED_CAL = ql.UnitedStates(ql.UnitedStates.FederalReserve)


@pytest.fixture
def prime_index():
    # Provide a flat forwarding curve so QL can project future coupons
    handle = ql.RelinkableYieldTermStructureHandle()
    flat = ql.FlatForward(ql.Date(2, 1, 2024), 0.085, ql.Actual365Fixed())
    handle.linkTo(flat)
    idx = PrimeIndex(forwarding=handle)
    ql.Settings.instance().evaluationDate = ql.Date(15, 6, 2024)
    # Seed fixings for every business day Jan–Jun 2024
    d = ql.Date(2, 1, 2024)
    end = ql.Date(15, 6, 2024)
    while d <= end:
        if _FED_CAL.isBusinessDay(d):
            idx.addFixing(d, 0.085)
        d += 1
    yield idx
    ql.IndexManager.instance().clearHistory(idx.name())


@pytest.fixture
def bullet_loan(prime_index):
    return VariableRateLoan(
        face_value=10_000_000,
        spread=0.025,
        issue_date=ql.Date(2, 1, 2024),
        maturity=ql.Period(5, ql.Years),
        ibor_index=prime_index,
        repricing_frequency=ql.Period(1, ql.Months),
    )


class TestVariableRateLoanConstruction:
    def test_instrument_type(self, bullet_loan) -> None:
        assert bullet_loan.instrument_type == InstrumentType.VARIABLE_RATE_LOAN

    def test_face_value(self, bullet_loan) -> None:
        assert bullet_loan.face_value == 10_000_000.0

    def test_spread(self, bullet_loan) -> None:
        assert bullet_loan.spread == 0.025

    def test_ql_instrument_not_none(self, bullet_loan) -> None:
        assert bullet_loan.ql_instrument is not None

    def test_issue_and_maturity_dates(self, bullet_loan) -> None:
        assert bullet_loan.issue_date == datetime.date(2024, 1, 2)
        assert bullet_loan.maturity_date == datetime.date(2029, 1, 2)

    def test_repricing_frequency_set(self, bullet_loan) -> None:
        assert bullet_loan.repricing_frequency == ql.Period(1, ql.Months)


class TestVariableRateLoanSchedule:
    def test_payment_schedule_three_tuple(self, bullet_loan) -> None:
        interest, principal, outstanding = bullet_loan.payment_schedule()
        assert len(interest) > 0
        assert len(principal) > 0
        assert len(outstanding) > 0

    def test_bullet_single_redemption(self, bullet_loan) -> None:
        _, principal, _ = bullet_loan.payment_schedule()
        assert len(principal) == 1
        assert principal[0][1] == pytest.approx(10_000_000, rel=1e-2)

    def test_sinking_multiple_redemptions(self, prime_index) -> None:
        loan = VariableRateLoan(
            face_value=10_000_000,
            spread=0.025,
            issue_date=ql.Date(2, 1, 2024),
            maturity=ql.Period(5, ql.Years),
            ibor_index=prime_index,
            principal_repayment_mode=PrincipalRepaymentMode.SINKING,
        )
        _, principal, _ = loan.payment_schedule()
        assert len(principal) > 1


class TestVariableRateLoanRepricingDate:
    def test_repricing_date_returns_as_of_plus_frequency(self, bullet_loan) -> None:
        rd = bullet_loan.repricing_date(datetime.date(2024, 3, 15))
        assert rd == datetime.date(2024, 4, 15)

    def test_notional_bullet_before_maturity(self, bullet_loan) -> None:
        assert bullet_loan.notional(datetime.date(2024, 6, 1)) == pytest.approx(10_000_000, rel=1e-2)
