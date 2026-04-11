"""Tests for core accounting accounts."""

# ruff: noqa: S101
import pytest

from brms.core.models.accounting.accounts import AccountType, CompositeTAccount, TAccount


@pytest.fixture
def composite_t_account() -> CompositeTAccount:
    """Fixture for creating a CompositeTAccount object."""
    return CompositeTAccount("Total Assets", AccountType.ASSET)


def test_add_t_account(composite_t_account: CompositeTAccount) -> None:
    """Test adding a T-account to a composite T-account."""
    t_account = TAccount("Some assets", AccountType.ASSET, debit=100)
    composite_t_account.add_sub_account(t_account)
    assert t_account in composite_t_account.sub_accounts
    assert composite_t_account.debit_value == t_account.debit_value


def test_remove_t_account(composite_t_account: CompositeTAccount) -> None:
    """Test removing a T-account from a composite T-account."""
    t_account = TAccount("Some assets", AccountType.ASSET, debit=100)
    composite_t_account.add_sub_account(t_account)
    composite_t_account.remove_sub_account(t_account)
    assert t_account not in composite_t_account.sub_accounts
    assert composite_t_account.debit_value == 0


def test_update_t_account_value(composite_t_account: CompositeTAccount) -> None:
    """Test updating the value of a T-account in a composite T-account."""
    t_account = TAccount("Some assets", AccountType.ASSET, debit=100)
    composite_t_account.add_sub_account(t_account)
    t_account.debit(100)
    assert composite_t_account.debit_value == 200  # noqa: PLR2004
    assert composite_t_account.credit_value == 0


def test_t_account_equal_debits_credits(composite_t_account: CompositeTAccount) -> None:
    """Test a T-account with equal debits and credits within a composite."""
    t_account = TAccount("Some assets", AccountType.ASSET, debit=100, credit=100)
    composite_t_account.add_sub_account(t_account)
    assert t_account.debit_value == t_account.credit_value
    assert composite_t_account.debit_value == composite_t_account.credit_value

    t_account.debit(1000)
    assert t_account.debit_value != t_account.credit_value


@pytest.mark.skip("Subaccounts may have different types, e.g., Trading Income: Gain (income) and Loss (expense)")
def test_t_account_type_mismatch(composite_t_account: CompositeTAccount) -> None:
    """Test adding a T-account with a mismatched type to a composite T-account."""
    t_account = TAccount("Interest income", AccountType.INCOME, credit=100)
    with pytest.raises(ValueError):  # noqa: PT011
        composite_t_account.add_sub_account(t_account)


def test_set_value_directly_on_composite_t_account(composite_t_account: CompositeTAccount) -> None:
    """Test setting values directly on a composite T-account should raise an error."""
    composite_t_account.debit_value = 100  # no error since the composite account has no sub accounts

    t_account = TAccount("Some assets", AccountType.ASSET, debit=100)
    composite_t_account.add_sub_account(t_account)
    with pytest.raises(ValueError):  # noqa: PT011
        composite_t_account.credit_value = 100


def test_t_account_has_no_observable_methods() -> None:
    """Verify that TAccount no longer inherits from Observable."""
    account = TAccount("Test", AccountType.ASSET)
    assert not hasattr(account, "add_observer")
    assert not hasattr(account, "remove_observer")
    assert not hasattr(account, "notify_observers")
    assert not hasattr(account, "_observers")


def test_composite_propagates_through_parent_chain() -> None:
    """Test that value changes propagate up through nested composite accounts."""
    grandparent = CompositeTAccount("Grandparent", AccountType.ASSET)
    parent = CompositeTAccount("Parent", AccountType.ASSET)
    child = TAccount("Child", AccountType.ASSET)

    grandparent.add_sub_account(parent)
    parent.add_sub_account(child)

    child.debit(500)
    assert parent.debit_value == 500  # noqa: PLR2004
    assert grandparent.debit_value == 500  # noqa: PLR2004


def test_opening_balance_equity_exists() -> None:
    """BankChartOfAccounts has an Opening Balance Equity temporary account."""
    from brms.core.models.accounting.bank_accounts import BankChartOfAccounts

    coa = BankChartOfAccounts()
    assert hasattr(coa, "opening_balance_equity")
    assert coa.opening_balance_equity.name == "Opening Balance Equity"
    assert coa.opening_balance_equity.is_temporary_account is True
    assert coa.opening_balance_equity.type.value == "Equity"


if __name__ == "__main__":
    pytest.main([__file__])
