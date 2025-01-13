import datetime

import pytest

from brms.accounting.account import AccountBalances, AccountType, ChartOfAccountsBuilder, TAccount
from brms.accounting.journal import SimpleEntry
from brms.accounting.ledger import Ledger
from brms.accounting.report import Report
from brms.accounting.statement_viewer import HTMLStatementViewer


@pytest.fixture
def setup_ledger():
    cash_account = TAccount("Cash", AccountType.ASSET)
    inventory_account = TAccount("Inventory", AccountType.ASSET)

    equity_account = TAccount("Equity", AccountType.EQUITY)

    refund_account = TAccount("Refund", AccountType.INCOME, is_contra_account=True)
    revenue_account = TAccount("Sales", AccountType.INCOME, contra_accounts=[refund_account])

    salary_account = TAccount("Salary Expense", AccountType.EXPENSE)
    cogs_account = TAccount("COGS", AccountType.EXPENSE)

    builder = ChartOfAccountsBuilder()
    builder.add_asset_account(cash_account)
    builder.add_asset_account(inventory_account)
    builder.add_equity_account(equity_account)
    builder.add_income_account(revenue_account)
    builder.add_expense_account(cogs_account)
    builder.add_expense_account(salary_account)

    chart_of_accounts = builder.build()

    balances = AccountBalances({cash_account: 300, inventory_account: 2200, equity_account: 2500})

    ledger = Ledger()
    ledger.add_accounts_from_chart(chart_of_accounts, balances)

    date = datetime.date(2025, 12, 31)

    # Post some entries to create balances
    ledger.post(SimpleEntry(cash_account, revenue_account, value=2675, date=date, description="Sell goods for cash"))
    ledger.post(SimpleEntry(refund_account, cash_account, value=375, date=date, description="Client refund"))
    ledger.post(SimpleEntry(cogs_account, inventory_account, value=2000, date=date, description="Cost of sales"))
    ledger.post(SimpleEntry(salary_account, cash_account, value=500, date=date, description="Pay salaries"))

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

    # The statements should look like:
    #
    #                     Trial Balance
    #  Account                       Debit   Credit
    #  Asset Account
    #    Cash                      2100.00     0.00
    #    Inventory                  200.00     0.00
    #  Liability Account
    #  Equity Account
    #    Equity                       0.00  2500.00
    #    Retained Earnings            0.00     0.00
    #  Income Account
    #    Sales                        0.00  2675.00
    #    Refund                     375.00     0.00
    #    Income Summary Account       0.00     0.00
    #  Expense Account
    #    COGS                      2000.00     0.00
    #    Salary Expense             500.00     0.00
    #  Total                       5175.00  5175.00
    #                               Date: 2025-12-31

    #        Income Statement
    #  Income               2300.00
    #    Sales              2300.00
    #  Expense              2500.00
    #    COGS               2000.00
    #    Salary Expense      500.00
    #  Profit              (200.00)
    #               Date: 2025-12-31

    #             Balance Sheet
    #  Assets
    #    Cash                      2100.00
    #    Inventory                  200.00
    #  Total assets                2300.00
    #  Liabilities
    #  Total liabilities              0.00
    #  Net assets                  2300.00
    #  Shareholders' equity
    #    Equity                    2500.00
    #    Retained Earnings          200.00
    #  Total shareholders' equity  2700.00
    #                      Date: 2025-12-31


if __name__ == "__main__":
    pytest.main([__file__])
