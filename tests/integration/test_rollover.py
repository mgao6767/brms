"""Maturing bonds can be rolled into a new bond of the same term at the market rate."""
# ruff: noqa: D103

from __future__ import annotations

import datetime
from decimal import Decimal

import pytest

from brms.core.enums import MeasurementBasis, PositionStatus
from tests.support.engine import flat_yields, make_bond, make_position, run_bank
from tests.support.reconcile import account_balance

_START = datetime.date(2021, 1, 4)
_MATURITY = datetime.date(2022, 7, 1)
_YIELDS = flat_yields(_START, datetime.date(2024, 12, 31), 0.03)


def _run(*, rollover: bool, until: datetime.date = datetime.date(2022, 8, 31)):  # noqa: ANN202
    bond = make_bond(id="R")
    pos = make_position(id="pos-R", instrument_id="R", basis=MeasurementBasis.FVOCI, acquired=_START,
                        cost=Decimal(520_000))
    cash: dict[datetime.date, Decimal] = {}

    def record(sim, day: datetime.date) -> None:  # noqa: ANN001
        cash[day] = account_balance(sim, "Cash and Cash Equivalents")

    sim = run_bank([bond], [pos], yields=_YIELDS, until=until, each_day=record, reinvest_maturities=rollover)
    return sim, cash


def test_maturing_bond_is_rolled_into_a_new_par_bond() -> None:
    sim, cash = _run(rollover=True)
    assert sim.bank.positions.get("pos-R").status == PositionStatus.CLOSED  # noqa: S101
    new = [p for p in sim.bank.positions.open_positions() if p.id.startswith("pos-R@")]
    assert len(new) == 1  # noqa: S101
    position = new[0]
    instrument = sim.bank.instruments.get(position.instrument_id)
    assert position.acquisition_date == _MATURITY  # noqa: S101
    assert position.measurement_basis == MeasurementBasis.FVOCI  # noqa: S101
    assert instrument.face_value == 500_000  # noqa: S101, PLR2004
    assert instrument.maturity_date == datetime.date(2024, 7, 1)  # noqa: S101
    assert instrument.coupon_rate == pytest.approx(0.03, abs=0.002)  # noqa: S101
    redemption_day_cash = cash[_MATURITY] - cash[_MATURITY - datetime.timedelta(days=1)]
    coupon = 12_361.11
    assert float(redemption_day_cash) == pytest.approx(coupon, abs=1)  # noqa: S101  (face reinvested)


def test_without_rollover_the_face_stays_in_cash() -> None:
    sim, cash = _run(rollover=False)
    assert not [p for p in sim.bank.positions.open_positions() if p.id.startswith("pos-R@")]  # noqa: S101
    redemption_day_cash = cash[_MATURITY] - cash[_MATURITY - datetime.timedelta(days=1)]
    assert float(redemption_day_cash) == pytest.approx(500_000 + 12_361.11, abs=1)  # noqa: S101


def test_rolled_bond_rolls_again() -> None:
    sim, _cash = _run(rollover=True, until=datetime.date(2024, 7, 15))
    open_ids = [p.id for p in sim.bank.positions.open_positions() if p.id.startswith("pos-R@")]
    assert len(open_ids) == 1  # noqa: S101
    assert open_ids[0].count("@") == 2  # noqa: S101, PLR2004
