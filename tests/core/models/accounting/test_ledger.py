"""Tests for core accounting ledger."""

# ruff: noqa: S101, PLR2004
import datetime

import pytest

from brms.core.models.accounting.bank_accounts import BankChartOfAccounts
from brms.core.models.accounting.journal import CompoundEntry, SimpleEntry
from brms.core.models.accounting.ledger import Ledger


@pytest.fixture
def coa() -> BankChartOfAccounts:
    """Fixture providing a fresh BankChartOfAccounts."""
    return BankChartOfAccounts()


@pytest.fixture
def ledger(coa: BankChartOfAccounts) -> Ledger:
    """Fixture providing a Ledger backed by the coa fixture."""
    return Ledger(coa)


def test_post_entry(ledger: Ledger, coa: BankChartOfAccounts) -> None:
    """Test posting a simple entry to the ledger."""
    ledger.post(SimpleEntry(
        debit_account=coa.cash_account,
        credit_account=coa.interest_income_account,
        value=1000.0,
        date=datetime.date(2025, 1, 1),
        description="Interest income",
    ))
    assert coa.cash_account.balance() == 1000.0
    assert coa.interest_income_account.balance() == 1000.0

    ledger.post(SimpleEntry(
        debit_account=coa.cash_account,
        credit_account=coa.debt_account,
        value=1000.0,
        date=datetime.date(2025, 1, 2),
        description="Borrowed money",
    ))
    assert coa.cash_account.balance() == 2000.0
    assert coa.interest_income_account.balance() == 1000.0
    assert coa.debt_account.balance() == 1000.0


def test_post_compound_entry(ledger: Ledger, coa: BankChartOfAccounts) -> None:
    """Test posting a compound entry to the ledger."""
    entry = CompoundEntry(
        debit_accounts={coa.cash_account: 500.0, coa.receivable_account: 500.0},
        credit_accounts={coa.interest_income_account: 1000.0},
        date=datetime.date(2025, 1, 1),
        description="Compound entry example",
    )
    ledger.post(entry)
    assert coa.cash_account.balance() == 500.0
    assert coa.receivable_account.balance() == 500.0
    assert coa.interest_income_account.balance() == 1000.0


def test_close_ledger(ledger: Ledger, coa: BankChartOfAccounts) -> None:
    """Test closing the ledger and verifying account balances."""
    date = datetime.date(2025, 12, 31)

    ledger.post(SimpleEntry(
        debit_account=coa.cash_account,
        credit_account=coa.interest_income_account,
        value=5000.0, date=date, description="Interest income",
    ))
    ledger.post(SimpleEntry(
        debit_account=coa.interest_expense_account,
        credit_account=coa.cash_account,
        value=2000.0, date=date, description="Expense entry",
    ))

    ledger.close_ledger(date)

    assert coa.interest_income_account.balance() == 0.0
    assert coa.interest_expense_account.balance() == 0.0

    assert coa.income_summary_account.balance() == 0.0
    assert coa.retained_earnings_account.balance() == 3000.0  # 5000 income - 2000 expense
