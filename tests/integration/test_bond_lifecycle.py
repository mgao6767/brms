"""Holding a bond to maturity leaves nothing behind, under every measurement basis."""
# ruff: noqa: D103

from __future__ import annotations

import datetime
from decimal import Decimal

import pytest

from brms.core.enums import MeasurementBasis, PositionStatus, TransactionType, ValuationType
from brms.core.rules.interest_accrual import scaled_accrued_amount
from brms.core.utils import pydate_to_qldate
from tests.support.engine import flat_yields, make_bond, make_position, run_bank, stepped_yields
from tests.support.reconcile import account_balance

_START = datetime.date(2021, 1, 4)
_END = datetime.date(2022, 7, 29)
_YIELDS = stepped_yields(_START, datetime.date(2021, 7, 1), _END, 0.03, 0.05)
_CENT = Decimal("0.01")
_EMPTY_ACCOUNTS = (
    "Investment Securities at Amortized Cost",
    "Investment Securities at FVOCI",
    "Assets at FVTPL",
    "Accrued Interest Receivable",
    "Unrealized OCI Gain",
    "Unrealized OCI Loss",
)
_BASES = [MeasurementBasis.AMORTIZED_COST, MeasurementBasis.FVOCI, MeasurementBasis.FVTPL]


def _hold(basis: MeasurementBasis, clean: Decimal, acquired: datetime.date = _START):  # noqa: ANN202
    bond = make_bond(id="R")
    accrued = scaled_accrued_amount(bond.ql_instrument, pydate_to_qldate(acquired))
    cost = clean + accrued
    pos = make_position(id="pos-R", instrument_id="R", basis=basis, acquired=acquired, cost=cost)
    return run_bank([bond], [pos], yields=_YIELDS, until=_END), cost


@pytest.mark.parametrize("basis", _BASES)
@pytest.mark.parametrize("clean", [Decimal(520_000), Decimal(480_000)])
def test_hold_to_maturity_leaves_nothing_behind(basis: MeasurementBasis, clean: Decimal) -> None:
    sim, _cost = _hold(basis, clean)
    assert sim.bank.positions.get("pos-R").status == PositionStatus.CLOSED  # noqa: S101
    for name in _EMPTY_ACCOUNTS:
        assert abs(account_balance(sim, name)) <= _CENT, name  # noqa: S101
    settlements = [
        t for t in sim.transaction_log.by_position("pos-R") if t.type == TransactionType.MATURITY_SETTLEMENT
    ]
    assert len(settlements) == 1  # noqa: S101


@pytest.mark.parametrize("basis", _BASES)
@pytest.mark.parametrize(
    ("clean", "acquired"),
    [(Decimal(520_000), _START), (Decimal(480_000), _START), (Decimal(510_000), datetime.date(2021, 3, 15))],
)
def test_life_income_equals_cash_in_minus_cash_out(
    basis: MeasurementBasis, clean: Decimal, acquired: datetime.date,
) -> None:
    sim, cost = _hold(basis, clean, acquired)
    coupons = sum(
        (t.amount for t in sim.transaction_log.by_position("pos-R") if t.type == TransactionType.INTEREST_SETTLEMENT),
        Decimal(0),
    )
    income = (
        account_balance(sim, "Interest Income")
        + account_balance(sim, "Unrealized Trading Gain")
        - account_balance(sim, "Unrealized Trading Loss")
    )
    assert abs(income - (coupons + Decimal(500_000) - cost)) <= Decimal("0.05")  # noqa: S101


def test_one_bond_maturing_leaves_the_other_untouched() -> None:
    short = make_bond(id="R")
    long = make_bond(id="L", maturity=datetime.date(2025, 7, 1))
    positions = [
        make_position(
            id="pos-R", instrument_id="R", basis=MeasurementBasis.FVTPL, acquired=_START, cost=Decimal(520_000),
        ),
        make_position(
            id="pos-L", instrument_id="L", basis=MeasurementBasis.FVTPL, acquired=_START, cost=Decimal(540_000),
        ),
    ]
    day = datetime.date(2022, 7, 1)
    sim = run_bank([short, long], positions, yields=_YIELDS, until=day)
    carrying = sim.valuation_store.get("pos-L", day, ValuationType.CARRYING_VALUE)
    assert abs(account_balance(sim, "Assets at FVTPL") - carrying) <= _CENT  # noqa: S101
    assert account_balance(sim, "Realized Trading Loss") == 0  # noqa: S101


def test_bond_maturing_on_a_non_business_day() -> None:
    bond = make_bond(id="N", maturity=datetime.date(2023, 1, 1))
    pos = make_position(
        id="pos-N", instrument_id="N", basis=MeasurementBasis.FVOCI, acquired=_START, cost=Decimal(510_000),
    )
    end = datetime.date(2023, 1, 31)
    sim = run_bank([bond], [pos], yields=flat_yields(_START, end), until=end)
    assert sim.bank.positions.get("pos-N").status == PositionStatus.CLOSED  # noqa: S101
    settlements = [
        t for t in sim.transaction_log.by_position("pos-N") if t.type == TransactionType.MATURITY_SETTLEMENT
    ]
    assert len(settlements) == 1  # noqa: S101
    assert settlements[0].date == bond.payment_schedule()[-1][0]  # noqa: S101
    for name in _EMPTY_ACCOUNTS:
        assert abs(account_balance(sim, name)) <= _CENT, name  # noqa: S101
