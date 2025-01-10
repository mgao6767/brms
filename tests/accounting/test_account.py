import pytest

from brms.accounting.account import AccountType, ChartOfAccounts, ChartOfAccountsBuilder, CompositeTAccount, TAccount


@pytest.fixture
def composite_t_account() -> CompositeTAccount:
    """Fixture for creating a CompositeTAccount object."""
    return CompositeTAccount("Total Assets", AccountType.ASSET)


def test_add_t_account(composite_t_account):
    """Test adding a T-account to a composite T-account."""
    t_account = TAccount("Some assets", AccountType.ASSET, debit=100)
    composite_t_account.add(t_account)
    assert t_account in composite_t_account.sub_accounts
    assert composite_t_account.debit_value == t_account.debit_value


def test_remove_t_account(composite_t_account):
    """Test removing a T-account from a composite T-account."""
    t_account = TAccount("Some assets", AccountType.ASSET, debit=100)
    composite_t_account.add(t_account)
    composite_t_account.remove(t_account)
    assert t_account not in composite_t_account.sub_accounts
    assert composite_t_account.debit_value == 0


def test_update_t_account_value(composite_t_account):
    """Test updating the value of a T-account in a composite T-account."""
    t_account = TAccount("Some assets", AccountType.ASSET, debit=100)
    composite_t_account.add(t_account)
    t_account.debit(100)
    assert composite_t_account.debit_value == 200
    assert composite_t_account.credit_value == 0


def test_t_account_balanced(composite_t_account):
    """Test if a T-account is balanced within a composite T-account."""
    t_account = TAccount("Some assets", AccountType.ASSET, debit=100, credit=100)
    composite_t_account.add(t_account)
    assert t_account.is_balanced()
    assert composite_t_account.debit_value == composite_t_account.credit_value

    t_account.debit(1000)
    assert not t_account.is_balanced()


def test_t_account_type_mismatch(composite_t_account):
    """Test adding a T-account with a mismatched type to a composite T-account."""
    t_account = TAccount("Interest income", AccountType.INCOME, credit=100)
    with pytest.raises(ValueError):
        composite_t_account.add(t_account)


def test_set_value_directly_on_composite_t_account(composite_t_account):
    """Test setting values directly on a composite T-account should raise an error."""
    composite_t_account.debit_value = 100  # no error since the composite account has no sub accounts

    t_account = TAccount("Some assets", AccountType.ASSET, debit=100)
    composite_t_account.add(t_account)
    with pytest.raises(ValueError):
        composite_t_account.credit_value = 100


def test_chart_of_accounts_initialization():
    """Test the initialization of ChartOfAccounts."""
    chart_of_accounts = ChartOfAccounts()
    assert chart_of_accounts.assets == []
    assert chart_of_accounts.equities == []
    assert chart_of_accounts.liabilities == []
    assert chart_of_accounts.income == []
    assert chart_of_accounts.expenses == []
    assert chart_of_accounts.income_summary_account.name == "Income Summary Account"
    assert chart_of_accounts.retained_earnings_account.name == "Retained Earnings Account"


def test_chart_of_accounts():
    """Test the initialization of ChartOfAccounts."""
    chart_of_accounts = ChartOfAccounts(
        assets=[CompositeTAccount("Assets", AccountType.ASSET)],
        liabilities=[CompositeTAccount("Liability", AccountType.LIABILITY)],
        equities=[CompositeTAccount("Equity", AccountType.EQUITY)],
        income=[CompositeTAccount("Income", AccountType.INCOME)],
        expenses=[CompositeTAccount("Expense", AccountType.EXPENSE)],
    )
    assert len(chart_of_accounts.assets) == 1
    assert len(chart_of_accounts.liabilities) == 1
    assert len(chart_of_accounts.equities) == 1
    assert len(chart_of_accounts.income) == 1
    assert len(chart_of_accounts.expenses) == 1


def test_chart_of_accounts_builder():
    """Test the ChartOfAccountsBuilder."""
    cash_and_liquid_assets = CompositeTAccount("Cash and liquid assets", AccountType.ASSET)
    cash_account = TAccount("Cash", account_type=AccountType.ASSET, debit=10000, credit=0)
    cash_and_liquid_assets.add(cash_account)
    cash_and_liquid_assets.add(TAccount("Liquid assets", AccountType.ASSET, debit=200))

    accounts_receivable_account = TAccount("Accounts Receivable", account_type=AccountType.ASSET, debit=5000, credit=0)
    common_stock_account = TAccount("Common Stock", account_type=AccountType.EQUITY, debit=0, credit=15000)
    accounts_payable_account = TAccount("Accounts Payable", account_type=AccountType.LIABILITY, debit=0, credit=2000)
    service_revenue_account = TAccount("Service Revenue", account_type=AccountType.INCOME, debit=0, credit=8000)
    salaries_expense_account = TAccount("Salaries Expense", account_type=AccountType.EXPENSE, debit=3000, credit=0)

    builder = ChartOfAccountsBuilder()

    builder.add_asset_account(cash_and_liquid_assets)
    builder.add_asset_account(accounts_receivable_account)
    builder.add_equity_account(common_stock_account)
    builder.add_liability_account(accounts_payable_account)
    builder.add_income_account(service_revenue_account)
    builder.add_expense_account(salaries_expense_account)

    chart_of_accounts = builder.build()

    assert cash_and_liquid_assets in chart_of_accounts.assets
    assert accounts_receivable_account in chart_of_accounts.assets
    assert common_stock_account in chart_of_accounts.equities
    assert accounts_payable_account in chart_of_accounts.liabilities
    assert service_revenue_account in chart_of_accounts.income
    assert salaries_expense_account in chart_of_accounts.expenses


def test_chart_of_accounts_builder_incorrect_account_type():
    """Test the ChartOfAccountsBuilder with an incorrect account type."""
    builder = ChartOfAccountsBuilder()
    salaries_expense_account = TAccount("Salaries Expense", account_type=AccountType.EXPENSE)

    with pytest.raises(ValueError):
        builder.add_asset_account(salaries_expense_account)


if __name__ == "__main__":
    pytest.main([__file__])
