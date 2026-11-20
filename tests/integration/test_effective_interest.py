"""Premium and discount are amortised into interest income at the effective interest rate."""
# ruff: noqa: D103

from __future__ import annotations

import datetime
from decimal import Decimal

from brms.core.enums import MeasurementBasis, TransactionType, ValuationType
from tests.support.engine import flat_yields, make_bond, make_position, run_bank
from tests.support.reconcile import Check, account_balance

_YIELDS = flat_yields(datetime.date(2021, 1, 4), datetime.date(2022, 7, 29))
_START = datetime.date(2021, 1, 4)
_CHECKS = frozenset({Check.BALANCE, Check.ACCRUED_INTEREST, Check.AMORTIZED_COST_SECURITIES})


def _run(clean: Decimal, until: datetime.date, each_day=None):  # noqa: ANN001, ANN202
    bond = make_bond(id="R")
    pos = make_position(
        id="pos-R", instrument_id="R", basis=MeasurementBasis.AMORTIZED_COST, acquired=_START, cost=clean,
    )
    return run_bank([bond], [pos], yields=_YIELDS, until=until, checks=_CHECKS, each_day=each_day)


def test_premium_bond_account_tracks_amortized_cost() -> None:
    _run(Decimal(520_000), datetime.date(2022, 6, 30))


def test_discount_bond_account_tracks_amortized_cost() -> None:
    _run(Decimal(480_000), datetime.date(2022, 6, 30))


def test_premium_reduces_interest_income() -> None:
    end = datetime.date(2021, 7, 1)
    sim = _run(Decimal(520_000), end)
    coupon = Decimal("12291.67")  # coupon paid on 2021-07-01 for 2021-01-04..2021-07-01
    income = account_balance(sim, "Interest Income")
    amortized = sim.valuation_store.get("pos-R", end, ValuationType.AMORTIZED_COST)
    assert abs(income - (coupon + (amortized - Decimal(520_000)))) <= Decimal("0.05")  # noqa: S101
    assert income < coupon  # noqa: S101


def test_amortization_posts_on_weekends() -> None:
    sim = _run(Decimal(520_000), datetime.date(2021, 1, 12))
    saturday = datetime.date(2021, 1, 9)
    types = {t.type for t in sim.transaction_log.by_position("pos-R") if t.date == saturday}
    assert TransactionType.PREMIUM_DISCOUNT_AMORTIZATION in types  # noqa: S101
