"""advance(date) over a gap processes every intervening calendar day."""
# ruff: noqa: D103

from __future__ import annotations

import datetime
from decimal import Decimal

from brms.core.enums import MeasurementBasis, TransactionType
from brms.core.services.reporting_service import ReportingService
from tests.support.engine import flat_yields, make_bond, make_position, run_bank

_START = datetime.date(2021, 1, 4)
_YIELDS = flat_yields(_START, datetime.date(2021, 12, 31))


def _engine():  # noqa: ANN202
    bond = make_bond(id="R")
    pos = make_position(
        id="pos-R", instrument_id="R", basis=MeasurementBasis.AMORTIZED_COST, acquired=_START, cost=Decimal(520_000),
    )
    return run_bank([bond], [pos], yields=_YIELDS, until=datetime.date(2021, 6, 25))


def test_advance_over_a_gap_processes_every_day() -> None:
    target = datetime.date(2021, 7, 6)
    daily = _engine()
    day = datetime.date(2021, 6, 26)
    while day <= target:
        daily.advance(day)
        day += datetime.timedelta(days=1)
    jumped = _engine()
    jumped.advance(target)

    assert jumped.current_date == target  # noqa: S101
    a = ReportingService().balance_sheet(daily.bank.ledger, date=target)
    b = ReportingService().balance_sheet(jumped.bank.ledger, date=target)
    rows_a = {r["account"]: r["balance"] for r in a["assets"] + a["liabilities"] + a["equity"]}
    rows_b = {r["account"]: r["balance"] for r in b["assets"] + b["liabilities"] + b["equity"]}
    assert rows_a.keys() == rows_b.keys()  # noqa: S101
    for name, value in rows_a.items():
        assert abs(value - rows_b[name]) <= 0.01, name  # noqa: S101, PLR2004
    coupon_day = datetime.date(2021, 7, 1)
    settled = jumped.transaction_log.by_type(TransactionType.INTEREST_SETTLEMENT)
    settlements = [t for t in settled if t.date == coupon_day]
    assert settlements  # noqa: S101
