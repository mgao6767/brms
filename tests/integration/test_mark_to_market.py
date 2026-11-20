"""Mark-to-market on clean prices, with OCI netted at account level and no per-position state."""
# ruff: noqa: D103

from __future__ import annotations

import datetime
import itertools
from decimal import Decimal

from brms.core.enums import MeasurementBasis, TransactionType, ValuationType
from brms.core.services.accounting_service import AccountingService
from tests.support.engine import flat_yields, make_bond, make_position, run_bank, stepped_yields
from tests.support.reconcile import Check, account_balance

_START = datetime.date(2021, 1, 4)
_END = datetime.date(2022, 7, 29)
_MOVING = stepped_yields(_START, datetime.date(2021, 7, 1), _END, 0.03, 0.05)
_FLAT = flat_yields(_START, _END)
_CENT = Decimal("0.01")


def _run(basis: MeasurementBasis, until: datetime.date, checks: frozenset[Check], yields=_MOVING, clean=Decimal(520_000)):  # noqa: ANN001, ANN202, E501
    bond = make_bond(id="R")
    pos = make_position(id="pos-R", instrument_id="R", basis=basis, acquired=_START, cost=clean)
    return run_bank([bond], [pos], yields=yields, until=until, checks=checks)


def test_fvtpl_account_tracks_fair_value() -> None:
    _run(
        MeasurementBasis.FVTPL, datetime.date(2022, 6, 30),
        frozenset({Check.BALANCE, Check.ACCRUED_INTEREST, Check.FVTPL_ASSETS}),
    )


def test_fvoci_account_and_aoci_reconcile() -> None:
    _run(
        MeasurementBasis.FVOCI, datetime.date(2022, 6, 30),
        frozenset({Check.BALANCE, Check.ACCRUED_INTEREST, Check.FVOCI_SECURITIES, Check.AOCI}),
    )


def test_aoci_holds_net_not_gross() -> None:
    day = datetime.date(2021, 9, 30)
    sim = _run(MeasurementBasis.FVOCI, day, frozenset({Check.BALANCE}))
    store = sim.valuation_store
    net = store.get("pos-R", day, ValuationType.CARRYING_VALUE) - store.get("pos-R", day, ValuationType.AMORTIZED_COST)
    assert net < 0  # noqa: S101
    assert account_balance(sim, "Unrealized OCI Gain") == 0  # noqa: S101
    assert abs(account_balance(sim, "Unrealized OCI Loss") + net) <= _CENT  # noqa: S101


def test_coupon_does_not_create_a_trading_loss() -> None:
    """On flat yields the coupon-day mark is ordinary pull-to-par drift, not a coupon-sized drop.

    The plan asked for |mark| <= 1, but an FVTPL bond bought at a premium drifts toward par by
    tens of currency units a day on a flat curve, so the coupon day's mark per calendar day is
    compared with that of the days before it. Marking dirty prices made it about -12,000.
    """
    coupon_day = datetime.date(2021, 7, 1)
    sim = _run(MeasurementBasis.FVTPL, coupon_day, frozenset({Check.BALANCE}), yields=_FLAT)
    marks = {
        t.date: t.amount for t in sim.transaction_log.by_position("pos-R") if t.type == TransactionType.MARK_TO_MARKET
    }
    days = sorted(marks)
    per_day = {d: marks[d] / (d - p).days for p, d in itertools.pairwise(days)}
    before = [v for d, v in per_day.items() if datetime.date(2021, 6, 21) <= d < coupon_day]
    assert before  # noqa: S101
    assert all(abs(per_day[coupon_day] - b) <= 2 for b in before), (per_day[coupon_day], before)  # noqa: S101, PLR2004


def test_fvoci_interest_income_equals_amortized_cost_bond() -> None:
    day = datetime.date(2021, 12, 31)
    oci = _run(MeasurementBasis.FVOCI, day, frozenset({Check.BALANCE}))
    oci_income = account_balance(oci, "Interest Income")
    held = _run(MeasurementBasis.AMORTIZED_COST, day, frozenset({Check.BALANCE}))
    assert abs(oci_income - account_balance(held, "Interest Income")) <= _CENT  # noqa: S101


def test_accounting_service_is_stateless() -> None:
    assert vars(AccountingService()) == {}  # noqa: S101
