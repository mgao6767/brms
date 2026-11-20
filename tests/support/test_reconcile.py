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


@pytest.mark.parametrize(
    ("account", "check"),
    [
        ("Investment Securities at Amortized Cost", "AMORTIZED_COST_SECURITIES"),
        ("Investment Securities at FVOCI", "FVOCI_SECURITIES"),
        ("Assets at FVTPL", "FVTPL_ASSETS"),
        ("Loans and Advances", "LOANS"),
        ("Accrued Interest Receivable", "ACCRUED_INTEREST"),
        ("Deposits", "DEPOSITS"),
        ("Unrealized OCI Gain", "AOCI"),
    ],
)
def test_reconcile_reports_mismatch(account: str, check: str) -> None:
    """A stray entry in any reconciled account is reported with that check's name."""
    sim = run_bank([], [], yields=flat_yields(datetime.date(2021, 1, 4), _UNTIL), until=_UNTIL)
    target = _lookup(sim, account)
    cash = _lookup(sim, "Cash and Cash Equivalents")
    debit, credit = (target, cash) if account not in {"Deposits", "Unrealized OCI Gain"} else (cash, target)
    sim.bank.ledger.post(SimpleEntry(debit_account=debit, credit_account=credit, value=100.0, date=_UNTIL))
    with pytest.raises(AssertionError, match=check):
        assert_books_reconcile(sim, _UNTIL)
