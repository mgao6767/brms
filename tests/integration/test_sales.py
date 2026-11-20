"""Selling securities at fair value, recycling accumulated OCI into profit or loss."""
# ruff: noqa: D103

from __future__ import annotations

import datetime
from decimal import Decimal

import pytest

from brms.core.enums import MeasurementBasis, PositionStatus, TransactionType, ValuationType
from brms.core.exceptions import UnsupportedPositionError, ValuationError
from tests.support.engine import make_bond, make_position, run_bank, stepped_yields
from tests.support.reconcile import account_balance

_START = datetime.date(2021, 1, 4)
_YIELDS = stepped_yields(_START, datetime.date(2021, 7, 1), datetime.date(2022, 6, 30), 0.02, 0.05)
_SALE = datetime.date(2021, 9, 15)  # a Wednesday after the rate rise


def _run(basis: MeasurementBasis, sale: datetime.date = _SALE, until: datetime.date = datetime.date(2021, 9, 30)):  # noqa: ANN202
    bond = make_bond(id="L", coupon=0.02, maturity=datetime.date(2030, 7, 1))  # near par at 2%, below par at 5%
    pos = make_position(id="pos-L", instrument_id="L", basis=basis, acquired=_START, cost=Decimal(500_000))
    pos.sale_date = sale
    seen: dict[datetime.date, dict[str, Decimal]] = {}

    def record(sim, day: datetime.date) -> None:  # noqa: ANN001
        store = sim.valuation_store
        seen[day] = {
            "cash": account_balance(sim, "Cash and Cash Equivalents"),
            "fair": store.get("pos-L", day, ValuationType.FAIR_VALUE),
            "accrued": store.get("pos-L", day, ValuationType.ACCRUED_INTEREST),
            "amortized": store.get("pos-L", day, ValuationType.AMORTIZED_COST),
        }

    sim = run_bank([bond], [pos], yields=_YIELDS, until=until, each_day=record)
    return sim, seen


def test_fvoci_sale_recycles_the_unrealised_loss() -> None:
    sim, seen = _run(MeasurementBasis.FVOCI)
    on_sale = seen[_SALE]
    loss = on_sale["amortized"] - on_sale["fair"]
    assert loss > 0  # noqa: S101
    assert sim.bank.positions.get("pos-L").status == PositionStatus.CLOSED  # noqa: S101
    assert float(account_balance(sim, "Unrealized OCI Loss")) == pytest.approx(0, abs=0.01)  # noqa: S101
    assert float(account_balance(sim, "Unrealized OCI Gain")) == pytest.approx(0, abs=0.01)  # noqa: S101
    assert float(account_balance(sim, "Realized OCI Loss")) == pytest.approx(float(loss), abs=0.01)  # noqa: S101
    proceeds = seen[_SALE]["cash"] - seen[_SALE - datetime.timedelta(days=1)]["cash"]
    assert float(proceeds) == pytest.approx(float(on_sale["fair"] + on_sale["accrued"]), abs=0.01)  # noqa: S101
    assert float(account_balance(sim, "Investment Securities at FVOCI")) == pytest.approx(0, abs=0.01)  # noqa: S101
    assert float(account_balance(sim, "Accrued Interest Receivable")) == pytest.approx(0, abs=0.01)  # noqa: S101
    sales = [t for t in sim.transaction_log.by_position("pos-L") if t.type == TransactionType.SECURITY_SALE]
    assert len(sales) == 1  # noqa: S101


def test_fvtpl_sale_books_no_further_gain_or_loss() -> None:
    sim, seen = _run(MeasurementBasis.FVTPL)
    assert sim.bank.positions.get("pos-L").status == PositionStatus.CLOSED  # noqa: S101
    assert float(account_balance(sim, "Realized Trading Loss")) == 0  # noqa: S101
    assert float(account_balance(sim, "Assets at FVTPL")) == pytest.approx(0, abs=0.01)  # noqa: S101


def test_selling_an_amortised_cost_position_is_not_supported() -> None:
    with pytest.raises(UnsupportedPositionError, match="pos-L"):
        _run(MeasurementBasis.AMORTIZED_COST)


def test_sale_needs_a_market_day() -> None:
    with pytest.raises(ValuationError, match="pos-L"):
        _run(MeasurementBasis.FVOCI, sale=datetime.date(2021, 9, 18))  # a Saturday
