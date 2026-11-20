"""The income statement over a date window."""
# ruff: noqa: D103

from __future__ import annotations

import datetime
from decimal import Decimal

from brms.core.enums import EntryKind, MeasurementBasis
from brms.core.models.accounting.journal import SimpleEntry
from brms.core.services.reporting_service import ReportingService
from tests.support.engine import flat_yields, make_bond, make_position, run_bank
from tests.support.reconcile import Check, account_balance

_START = datetime.date(2021, 1, 4)
_YIELDS = flat_yields(_START, datetime.date(2021, 12, 31))


def _run(each_day=None):  # noqa: ANN001, ANN202
    bond = make_bond(id="R")
    pos = make_position(
        id="pos-R", instrument_id="R", basis=MeasurementBasis.AMORTIZED_COST, acquired=_START, cost=Decimal(520_000),
    )
    return run_bank(
        [bond], [pos], yields=_YIELDS, until=datetime.date(2021, 12, 31), checks=frozenset({Check.BALANCE}),
        each_day=each_day,
    )


def test_income_statement_window() -> None:
    marks: dict[datetime.date, Decimal] = {}

    def record(sim, day: datetime.date) -> None:  # noqa: ANN001
        if day in (datetime.date(2021, 3, 31), datetime.date(2021, 6, 30)):
            marks[day] = account_balance(sim, "Interest Income")

    sim = _run(record)
    window = ReportingService().income_statement(
        sim.bank.ledger, start=datetime.date(2021, 4, 1), end=datetime.date(2021, 6, 30),
    )
    expected = marks[datetime.date(2021, 6, 30)] - marks[datetime.date(2021, 3, 31)]
    assert abs(Decimal(str(window["total_income"])) - expected) <= Decimal("0.01")  # noqa: S101


def test_income_statement_window_excludes_opening_and_closing_entries() -> None:
    sim = _run()
    ledger = sim.bank.ledger
    income = next(a for a in ledger.chart_of_accounts.all_accounts() if a.name == "Interest Income")
    summary = ledger.chart_of_accounts.income_summary_account
    day = datetime.date(2021, 5, 1)
    window = (datetime.date(2021, 4, 1), datetime.date(2021, 6, 30))
    before = ReportingService().income_statement(ledger, start=window[0], end=window[1])["total_income"]
    for kind in (EntryKind.OPENING, EntryKind.CLOSING):
        ledger.post(
            SimpleEntry(debit_account=summary, credit_account=income, value=1000.0, date=day, kind=kind),
        )
    after = ReportingService().income_statement(ledger, start=window[0], end=window[1])["total_income"]
    assert abs(after - before) <= 0.01  # noqa: S101, PLR2004
