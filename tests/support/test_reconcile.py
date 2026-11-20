"""Tests for the reconciliation helper itself."""

from __future__ import annotations

import datetime

import pytest

from brms.core.models.accounting.journal import SimpleEntry
from tests.support.engine import flat_yields, run_bank
from tests.support.reconcile import assert_books_reconcile

_UNTIL = datetime.date(2021, 2, 26)


def _lookup(sim, name):  # noqa: ANN001, ANN202
    return next(a for a in sim.bank.ledger.chart_of_accounts.all_accounts() if a.name == name)


def test_cash_only_bank_reconciles() -> None:
    """A bank funded only by equity passes every check every day."""
    run_bank([], [], yields=flat_yields(datetime.date(2021, 1, 4), _UNTIL), until=_UNTIL)


def test_reconcile_reports_mismatch() -> None:
    """A stray entry in a control account is reported with the check's name."""
    sim = run_bank([], [], yields=flat_yields(datetime.date(2021, 1, 4), _UNTIL), until=_UNTIL)
    sim.bank.ledger.post(
        SimpleEntry(
            debit_account=_lookup(sim, "Assets at FVTPL"),
            credit_account=_lookup(sim, "Cash and Cash Equivalents"),
            value=100.0,
            date=_UNTIL,
            description="stray",
        ),
    )
    with pytest.raises(AssertionError, match="FVTPL_ASSETS"):
        assert_books_reconcile(sim, _UNTIL)
