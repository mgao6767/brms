import datetime

import pytest

from brms.accounting.account import AccountType, ChartOfAccountsBuilder, TAccount
from brms.accounting.journal import CompoundEntry, SimpleEntry
from brms.accounting.ledger import Ledger


@pytest.fixture
def setup_accounts():
    cash_account = TAccount("Cash", AccountType.ASSET)
    debt_account = TAccount("Debt", AccountType.LIABILITY)
    refund_account = TAccount("Refund", AccountType.INCOME, is_contra_account=True)
    revenue_account = TAccount("Revenue", AccountType.INCOME, contra_accounts=[refund_account])
    expense_account = TAccount("Expense", AccountType.EXPENSE)
    account_receivable_account = TAccount("Account Receivable", AccountType.ASSET)

    return (
        cash_account,
        debt_account,
        account_receivable_account,
        refund_account,
        revenue_account,
        expense_account,
    )


@pytest.fixture
def setup_ledger(setup_accounts):
    cash_account, debt_account, account_receivable_account, _, revenue_account, expense_account = setup_accounts
    builder = ChartOfAccountsBuilder()
    builder.add_asset_account(cash_account)
    builder.add_asset_account(account_receivable_account)
    builder.add_liability_account(debt_account)
    builder.add_income_account(revenue_account)
    builder.add_expense_account(expense_account)
    chart_of_accounts = builder.build()
    ledger = Ledger()
    ledger.add_accounts_from_chart(chart_of_accounts)
    return ledger


def test_add_account(setup_ledger):
    ledger = setup_ledger
    new_account = TAccount(name="New Account", account_type=AccountType.ASSET)
    ledger._add_account(new_account)
    assert ledger.get_account("New Account") == new_account


def test_get_account_not_exist(setup_ledger):
    ledger = setup_ledger
    with pytest.raises(ValueError, match="Account with name NonExistentAccount not found"):
        ledger.get_account("NonExistentAccount")


def test_get_account(setup_ledger):
    ledger = setup_ledger
    account = ledger.get_account("Cash")
    assert account.name == "Cash"


def test_post_entry(setup_ledger):
    ledger = setup_ledger
    entry = SimpleEntry(
        debit_account=ledger.get_account("Cash"),
        credit_account=ledger.get_account("Revenue"),
        value=1000.0,
        date=datetime.date(2025, 1, 1),
        description="Service revenue",
    )
    ledger.post(entry)
    assert ledger.get_account("Cash").balance() == 1000.0
    assert ledger.get_account("Revenue").balance() == 1000.0

    entry = SimpleEntry(
        debit_account=ledger.get_account("Cash"),
        credit_account=ledger.get_account("Debt"),
        value=1000.0,
        date=datetime.date.today(),
        description="Borrowed money",
    )
    ledger.post(entry)
    assert ledger.get_account("Cash").balance() == 2000.0
    assert ledger.get_account("Revenue").balance() == 1000.0
    assert ledger.get_account("Debt").balance() == 1000.0


def test_post_compound_entry(setup_ledger):
    ledger = setup_ledger
    debit_accounts = {
        ledger.get_account("Cash"): 500.0,
        ledger.get_account("Account Receivable"): 500.0,
    }
    credit_accounts = {
        ledger.get_account("Revenue"): 1000.0,
    }
    entry = CompoundEntry(
        debit_accounts=debit_accounts,
        credit_accounts=credit_accounts,
        date=datetime.date(2025, 1, 1),
        description="Compound entry example",
    )
    ledger.post(entry)
    assert ledger.get_account("Cash").balance() == 500.0
    assert ledger.get_account("Account Receivable").balance() == 500.0
    assert ledger.get_account("Revenue").balance() == 1000.0


def test_add_accounts_from_chart(setup_accounts, setup_ledger):
    (
        cash_account,
        debt_account,
        _,
        _,
        revenue_account,
        _,
    ) = setup_accounts
    ledger = setup_ledger
    assert ledger.get_account("Cash") is cash_account
    assert ledger.get_account("Debt") is debt_account
    assert ledger.get_account("Revenue") is revenue_account


def test_close_ledger(setup_accounts, setup_ledger):
    cash_account, debt_account, account_receivable_account, refund_account, revenue_account, expense_account = (
        setup_accounts
    )
    ledger = setup_ledger
    date = datetime.date(2025, 12, 31)

    # Post some entries to create balances
    ledger.post(
        SimpleEntry(
            debit_account=cash_account,
            credit_account=revenue_account,
            value=5000.0,
            date=date,
            description="Revenue entry",
        ),
    )
    ledger.post(
        SimpleEntry(
            debit_account=expense_account,
            credit_account=cash_account,
            value=2000.0,
            date=date,
            description="Expense entry",
        ),
    )

    # Close the ledger
    ledger.close_ledger(date)

    # Check that income and expense accounts are closed
    assert ledger.get_account("Revenue").balance() == 0.0
    assert ledger.get_account("Expense").balance() == 0.0

    # Check that Income Summary is closed to Retained Earnings
    income_summary = ledger.income_summary_account
    retained_earnings = ledger.retained_earnings_account
    assert income_summary.balance() == 0.0
    assert retained_earnings.balance() == 3000.0  # 5000 (revenue) - 2000 (expense)


if __name__ == "__main__":
    pytest.main([__file__])
