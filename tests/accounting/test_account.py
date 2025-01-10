import pytest

from brms.accounting.account import AccountType, CompositeTAccount, TAccount


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


if __name__ == "__main__":
    pytest.main()
