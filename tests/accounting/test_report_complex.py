import datetime
import pytest
from brms.accounting.account import AccountType, ChartOfAccountsBuilder, TAccount, CompositeTAccount, AccountBalances
from brms.accounting.journal import SimpleEntry
from brms.accounting.ledger import Ledger
from brms.accounting.report import Report
from brms.accounting.statement_viewer import HTMLStatementViewer


@pytest.fixture
def setup_ledger():
    cash_account = TAccount("Cash and Cash Equivalents", AccountType.ASSET)
    loan_account = TAccount("Loan and Advances", AccountType.ASSET)
    account_receivable_account = TAccount("Account Receivable", AccountType.ASSET)
    ppe_account = TAccount("Property, Plant and Equipment", AccountType.ASSET)

    deposit_account = CompositeTAccount("Deposits and Other Borrowings", AccountType.LIABILITY)
    customer_deposit_account = TAccount("Deposits", AccountType.LIABILITY)
    borrowings_account = TAccount("Other Borrowings", AccountType.LIABILITY)
    account_payable_account = TAccount("Account Payable", AccountType.LIABILITY)
    deposit_account.add(customer_deposit_account)
    deposit_account.add(borrowings_account)
    deposit_account.add(account_payable_account)

    equity_account = TAccount("Shareholders' Equity", AccountType.EQUITY)

    interest_income_account = CompositeTAccount("Interest Income", AccountType.INCOME)

    salary_account = TAccount("Salary Expense", AccountType.EXPENSE)
    interest_expense_account = TAccount("Interest Expense", AccountType.EXPENSE)

    builder = ChartOfAccountsBuilder()
    builder.add_asset_account(cash_account)
    builder.add_asset_account(account_receivable_account)
    builder.add_asset_account(loan_account)
    builder.add_asset_account(ppe_account)
    builder.add_liability_account(deposit_account)
    builder.add_equity_account(equity_account)
    builder.add_income_account(interest_income_account)
    builder.add_expense_account(interest_expense_account)
    builder.add_expense_account(salary_account)

    chart_of_accounts = builder.build()
    retained_earnings_account = chart_of_accounts.retained_earnings_account

    balances = AccountBalances(
        {
            cash_account: 12500,
            equity_account: 30000,
            ppe_account: 20000,
            retained_earnings_account: 2500,
        },
    )

    ledger = Ledger()
    ledger.add_accounts_from_chart(chart_of_accounts, balances)

    date = datetime.date(2025, 12, 31)

    # Post some entries to create balances
    ledger.post(
        SimpleEntry(
            debit_account=cash_account,
            credit_account=customer_deposit_account,
            value=50000.0,
            date=date,
            description="Customer deposits",
        ),
    )
    ledger.post(
        SimpleEntry(
            debit_account=cash_account,
            credit_account=borrowings_account,
            value=10000.0,
            date=date,
            description="Public borrowings",
        ),
    )
    ledger.post(
        SimpleEntry(
            debit_account=loan_account,
            credit_account=cash_account,
            value=65000.0,
            date=date,
            description="Loan issue",
        ),
    )
    ledger.post(
        SimpleEntry(
            debit_account=cash_account,
            credit_account=interest_income_account,
            value=2000,
            date=date,
            description="Interest income",
        ),
    )
    ledger.post(
        SimpleEntry(
            debit_account=interest_expense_account,
            credit_account=cash_account,
            value=1900,
            date=date,
            description="Interest expense",
        ),
    )
    ledger.post(
        SimpleEntry(
            debit_account=salary_account,
            credit_account=cash_account,
            value=2000,
            date=date,
            description="salary expense",
        ),
    )

    return ledger, date


def test_report_generation(setup_ledger):
    ledger, date = setup_ledger
    report = Report(ledger=ledger, viewer=HTMLStatementViewer(), date=date)

    html_trial_balance = report.print_trial_balance()
    assert "Trial Balance" in html_trial_balance

    html_income_statement = report.print_income_statement()
    assert "Income Statement" in html_income_statement

    html_balance_sheet = report.print_balance_sheet()
    assert "Balance Sheet" in html_balance_sheet

    print(html_trial_balance)
    print(html_income_statement)
    print(html_balance_sheet)


if __name__ == "__main__":
    pytest.main([__file__])
