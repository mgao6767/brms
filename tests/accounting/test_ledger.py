import datetime

import pytest

from brms.accounting.account import BankChartOfAccounts
from brms.accounting.journal import CompoundEntry, SimpleEntry
from brms.accounting.ledger import Ledger


@pytest.fixture
def setup_ledger() -> Ledger:
    """Fixture to set up a Ledger instance for testing."""
    return Ledger(BankChartOfAccounts())


def test_post_entry(setup_ledger: Ledger) -> None:
    """Test posting a simple entry to the ledger."""
    ledger = setup_ledger
    entry = SimpleEntry(
        debit_account=ledger.coa.cash_account,
        credit_account=ledger.coa.interest_income_account,
        value=1000.0,
        date=datetime.date(2025, 1, 1),
        description="Interest income",
    )
    ledger.post(entry)
    assert ledger.coa.cash_account.balance() == 1000.0
    assert ledger.coa.interest_income_account.balance() == 1000.0

    entry = SimpleEntry(
        debit_account=ledger.coa.cash_account,
        credit_account=ledger.coa.debt_account,
        value=1000.0,
        date=datetime.date(2025, 1, 2),
        description="Borrowed money",
    )
    ledger.post(entry)
    assert ledger.coa.cash_account.balance() == 2000.0
    assert ledger.coa.interest_income_account.balance() == 1000.0
    assert ledger.coa.debt_account.balance() == 1000.0


def test_post_compound_entry(setup_ledger: Ledger) -> None:
    """Test posting a compound entry to the ledger."""
    ledger = setup_ledger
    debit_accounts = {
        ledger.coa.cash_account: 500.0,
        ledger.coa.receivable_account: 500.0,
    }
    credit_accounts = {
        ledger.coa.interest_income_account: 1000.0,
    }
    entry = CompoundEntry(
        debit_accounts=debit_accounts,
        credit_accounts=credit_accounts,
        date=datetime.date(2025, 1, 1),
        description="Compound entry example",
    )
    ledger.post(entry)
    assert ledger.coa.cash_account.balance() == 500.0
    assert ledger.coa.receivable_account.balance() == 500.0
    assert ledger.coa.interest_income_account.balance() == 1000.0


def test_close_ledger(setup_ledger: Ledger) -> None:
    """Test closing the ledger and verifying account balances."""
    ledger = setup_ledger
    date = datetime.date(2025, 12, 31)

    # Post some entries to create balances
    ledger.post(
        SimpleEntry(
            debit_account=ledger.coa.cash_account,
            credit_account=ledger.coa.interest_income_account,
            value=5000.0,
            date=date,
            description="Interest income",
        ),
    )
    ledger.post(
        SimpleEntry(
            debit_account=ledger.coa.interest_expense_account,
            credit_account=ledger.coa.cash_account,
            value=2000.0,
            date=date,
            description="Expense entry",
        ),
    )

    # Close the ledger
    ledger.close_ledger(date)

    # Check that accounts are closed
    assert ledger.coa.interest_income_account.balance() == 0.0
    assert ledger.coa.interest_expense_account.balance() == 0.0

    # Check that Income Summary is closed to Retained Earnings
    income_summary = ledger.coa.income_summary_account
    retained_earnings = ledger.coa.retained_earnings_account
    assert income_summary.balance() == 0.0
    assert retained_earnings.balance() == 3000.0  # 5000 (income) - 2000 (expense)


if __name__ == "__main__":
    pytest.main([__file__])
