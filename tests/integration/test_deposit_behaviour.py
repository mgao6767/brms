"""Deposits: balances that run off or are withdrawn, rates that pass through market moves."""
# ruff: noqa: D103

from __future__ import annotations

import datetime
import math
from decimal import Decimal

import pytest

from brms.core.enums import MeasurementBasis, PositionSide, ValuationType
from brms.core.models.instruments.deposits import Deposit
from tests.support.engine import make_position, run_bank, stepped_yields
from tests.support.reconcile import Check, account_balance

_START = datetime.date(2021, 1, 4)
_STEP = datetime.date(2021, 7, 1)
_END = datetime.date(2021, 12, 31)
_YIELDS = stepped_yields(_START, _STEP, datetime.date(2022, 12, 31), 0.01, 0.03)
_BALANCE = Decimal(1_000_000)
_CHECKS = frozenset({Check.BALANCE, Check.DEPOSITS, Check.INTEREST_PAYABLE})


def _deposit(**kwargs) -> Deposit:  # noqa: ANN003
    deposit = Deposit(name="Savings", **kwargs)
    deposit.id = "D"
    return deposit


def _run(deposit: Deposit, until: datetime.date = _END):  # noqa: ANN202
    pos = make_position(id="pos-D", instrument_id="D", basis=MeasurementBasis.NA, acquired=_START, cost=_BALANCE,
                        side=PositionSide.SHORT)
    return run_bank([deposit], [pos], yields=_YIELDS, until=until, checks=_CHECKS)


def test_fixed_rate_deposit_accrues_and_settles_monthly() -> None:
    sim = _run(_deposit(interest_rate=0.02), until=datetime.date(2021, 3, 1))
    expense = account_balance(sim, "Interest Expense")
    days = (datetime.date(2021, 3, 1) - _START).days
    assert float(expense) == pytest.approx(1_000_000 * 0.02 * days / 365, abs=0.05)  # noqa: S101
    payable = sim.valuation_store.get("pos-D", datetime.date(2021, 3, 1), ValuationType.ACCRUED_INTEREST)
    assert float(account_balance(sim, "Interest Payable")) == pytest.approx(float(payable), abs=0.01)  # noqa: S101


def test_beta_passes_through_part_of_a_rate_rise() -> None:
    sim = _run(_deposit(interest_rate=0.005, beta=0.4), until=datetime.date(2021, 8, 31))
    store = sim.valuation_store
    before = store.get("pos-D", datetime.date(2021, 6, 15), ValuationType.ACCRUED_INTEREST)
    before -= store.get("pos-D", datetime.date(2021, 6, 14), ValuationType.ACCRUED_INTEREST)
    after = store.get("pos-D", datetime.date(2021, 8, 15), ValuationType.ACCRUED_INTEREST)
    after -= store.get("pos-D", datetime.date(2021, 8, 14), ValuationType.ACCRUED_INTEREST)
    assert float(before) == pytest.approx(1_000_000 * 0.005 / 365, rel=1e-6)  # noqa: S101
    assert float(after) == pytest.approx(1_000_000 * (0.005 + 0.4 * 0.02) / 365, rel=1e-6)  # noqa: S101


def test_runoff_shrinks_the_balance_and_the_cash() -> None:
    sim = _run(_deposit(interest_rate=0.0, runoff_rate=0.2))
    years = (_END - _START).days / 365
    expected = 1_000_000 * math.exp(-0.2 * years)
    assert float(account_balance(sim, "Deposits")) == pytest.approx(expected, abs=0.05)  # noqa: S101
    assert float(sim.valuation_store.get("pos-D", _END, ValuationType.CARRYING_VALUE)) == pytest.approx(expected)  # noqa: S101


def test_scheduled_withdrawal() -> None:
    sim = _run(_deposit(interest_rate=0.0, withdrawals=[("2021-03-09", 0.25)]), until=datetime.date(2021, 3, 31))
    assert float(account_balance(sim, "Deposits")) == pytest.approx(750_000, abs=0.01)  # noqa: S101
    assert float(account_balance(sim, "Cash and Cash Equivalents")) == pytest.approx(2_000_000 + 750_000, abs=0.01)  # noqa: S101
