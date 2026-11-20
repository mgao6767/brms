"""Mortgage-backed securities in the engine: paydowns, fair value with prepayment, reconciliation."""
# ruff: noqa: D103, S101, PLR2004

from __future__ import annotations

import datetime
from decimal import Decimal

import pytest
import QuantLib as ql  # noqa: N813

from brms.core.enums import MeasurementBasis, PositionStatus, TransactionType, ValuationType
from brms.core.exceptions import UnsupportedPositionError
from brms.core.models.instruments.base import CreditRating, Issuer, IssuerType
from brms.core.models.instruments.mbs import MortgageBackedSecurity
from brms.core.utils import pydate_to_qldate
from tests.support.engine import make_position, run_bank, stepped_yields
from tests.support.reconcile import account_balance

_START = datetime.date(2021, 1, 4)
_STEP = datetime.date(2021, 7, 1)
_YIELDS = stepped_yields(_START, _STEP, datetime.date(2022, 12, 31), 0.01, 0.03)
_FACE = 1_000_000.0
_AGENCY = Issuer(name="Agency", issuer_type=IssuerType.PSE, credit_rating=CreditRating.AA_PLUS)


def _mbs(maturity: ql.Period = ql.Period(25, ql.Years)) -> MortgageBackedSecurity:  # noqa: B008
    mbs = MortgageBackedSecurity(
        face_value=_FACE, coupon_rate=0.02, issue_date=pydate_to_qldate(_START), maturity=maturity, issuer=_AGENCY,
    )
    mbs.id = "M"
    return mbs


def _run(basis: MeasurementBasis, until: datetime.date = datetime.date(2021, 9, 30), cost: float = _FACE, **kwargs):  # noqa: ANN003, ANN202
    pos = make_position(id="pos-M", instrument_id="M", basis=basis, acquired=_START, cost=Decimal(cost))
    return run_bank([kwargs.pop("instrument", None) or _mbs()], [pos], yields=_YIELDS, until=until, **kwargs)


@pytest.mark.parametrize("basis", [MeasurementBasis.AMORTIZED_COST, MeasurementBasis.FVOCI])
def test_mbs_reconciles_and_pays_down_at_the_pricing_speed(basis: MeasurementBasis) -> None:
    until = datetime.date(2021, 9, 30)
    sim = _run(basis, until)
    mbs = sim.bank.instruments.get("M")
    account = {MeasurementBasis.AMORTIZED_COST: "Investment Securities at Amortized Cost",
               MeasurementBasis.FVOCI: "Investment Securities at FVOCI"}[basis]
    amortized = sim.valuation_store.get("pos-M", until, ValuationType.AMORTIZED_COST)
    assert float(amortized) == pytest.approx(mbs.outstanding(until), abs=0.01)
    if basis == MeasurementBasis.AMORTIZED_COST:
        assert float(account_balance(sim, account)) == pytest.approx(mbs.outstanding(until), abs=0.01)
    assert float(account_balance(sim, "Loans and Advances")) == 0
    paydowns = [t for t in sim.transaction_log.by_position("pos-M") if t.type == TransactionType.AMORTIZATION]
    assert len(paydowns) == 8  # Feb through Sep


def test_rate_rise_lowers_fair_value_and_books_an_oci_loss() -> None:
    seen: dict[datetime.date, Decimal] = {}

    def record(sim, day: datetime.date) -> None:  # noqa: ANN001
        fair = sim.valuation_store.get("pos-M", day, ValuationType.FAIR_VALUE)
        if fair is not None:
            seen[day] = fair / Decimal(str(sim.bank.instruments.get("M").outstanding(day)))

    sim = _run(MeasurementBasis.FVOCI, each_day=record)
    before = seen[datetime.date(2021, 6, 30)]
    after = seen[_STEP]
    assert after < before - Decimal("0.10")  # a 200bp rise costs over 10 points on a long pool
    assert account_balance(sim, "Unrealized OCI Loss") > 0


def test_fair_value_on_the_acquisition_curve_is_close_to_cost() -> None:
    sim = _run(MeasurementBasis.FVOCI, until=datetime.date(2021, 1, 6), calibrate_spreads=True)
    fair = sim.valuation_store.get("pos-M", datetime.date(2021, 1, 5), ValuationType.FAIR_VALUE)
    assert float(fair) == pytest.approx(_FACE, rel=1e-3)  # spread calibrated to the price paid


def test_pool_runs_off_and_closes() -> None:
    sim = _run(MeasurementBasis.AMORTIZED_COST, until=datetime.date(2022, 2, 10),
               instrument=_mbs(maturity=ql.Period(1, ql.Years)))
    assert sim.bank.positions.get("pos-M").status == PositionStatus.CLOSED
    assert float(account_balance(sim, "Investment Securities at Amortized Cost")) == pytest.approx(0, abs=0.01)


def test_premium_purchase_is_rejected() -> None:
    with pytest.raises(UnsupportedPositionError, match="pos-M"):
        _run(MeasurementBasis.AMORTIZED_COST, cost=1_020_000.0, until=datetime.date(2021, 1, 10))


def test_fvtpl_is_rejected() -> None:
    with pytest.raises(UnsupportedPositionError, match="pos-M"):
        _run(MeasurementBasis.FVTPL, until=datetime.date(2021, 1, 10))


def test_eve_reprojects_prepayments_under_each_shock() -> None:
    from brms.core.metrics.risk.interest_rate_risk.eve import Scenario, eve_scenarios
    from brms.core.services.spreads import dirty_value

    day = datetime.date(2021, 3, 15)
    sim = _run(MeasurementBasis.AMORTIZED_COST, until=day, instrument=_mbs(maturity=ql.Period(30, ql.Years)))
    handle = sim.valuation_service.yield_handle
    mbs = sim.bank.instruments.get("M")
    result = eve_scenarios(sim.bank, handle, day)
    assert float(result.base_position_pv["pos-M"]) == pytest.approx(
        dirty_value(mbs.projected_leg(handle, day), handle, day), rel=1e-9,
    )
    # Falling rates speed up prepayments, so the pool gains less than it loses when rates rise.
    up = -result.position_delta(Scenario.PARALLEL_UP, "pos-M")
    down = result.position_delta(Scenario.PARALLEL_DOWN, "pos-M")
    assert down < up
