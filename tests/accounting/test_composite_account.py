import pytest

from brms.accounting.base import Account, AccountType, CompositeAccount


@pytest.fixture
def composite_account() -> CompositeAccount:
    """Fixture for creating a CompositeAccount object."""
    return CompositeAccount("Assets", AccountType.ASSET)


def test_add_account(composite_account):
    """Test adding an account to a composite account."""
    account = Account("Cash", AccountType.ASSET)
    composite_account.add(account)
    assert account in composite_account.accounts
    assert composite_account.value == account.value


def test_add_composite_account(composite_account):
    """Test adding a composite account to a composite account."""
    sub_composite_account = CompositeAccount("SubAssets", AccountType.ASSET)
    sub_composite_account.value = 100
    composite_account.add(sub_composite_account)
    assert sub_composite_account in composite_account.accounts
    assert composite_account.value == sub_composite_account.value


def test_remove_account(composite_account):
    """Test removing an account from a composite account."""
    account = Account("Cash", AccountType.ASSET)
    composite_account.add(account)
    composite_account.remove(account)
    assert account not in composite_account.accounts
    assert composite_account.value == 0


def test_update_account_value(composite_account):
    """Test updating the value of an account in a composite account."""
    account = Account("Cash", AccountType.ASSET, value=100)
    composite_account.add(account)
    account.value = 200
    assert composite_account.value == 200

    account = Account("Cash", AccountType.ASSET, value=100)
    composite_account.add(account)
    assert composite_account.value == 300


def test_account_type_mismatch(composite_account):
    """Test adding an account with a mismatched type to a composite account."""
    account = Account("Revenue", AccountType.INCOME)
    with pytest.raises(ValueError):
        composite_account.add(account)


if __name__ == "__main__":
    pytest.main()
