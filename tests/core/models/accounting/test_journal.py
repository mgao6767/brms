"""Tests for core accounting journal."""

# ruff: noqa: S101
import datetime

import pytest

from brms.core.models.accounting.accounts import AccountType, TAccount
from brms.core.models.accounting.journal import CompoundEntry, Journal, SimpleEntry


@pytest.fixture
def sample_accounts() -> tuple[TAccount, TAccount, TAccount]:
    """Fixture to create sample accounts for testing.

    Returns a tuple of cash, debt, and revenue accounts.
    """
    cash_account = TAccount("Cash", AccountType.ASSET)
    debt_account = TAccount("Debt", AccountType.LIABILITY)
    revenue_account = TAccount("Revenue", AccountType.INCOME)
    return cash_account, debt_account, revenue_account


@pytest.fixture
def sample_journal_entry(sample_accounts: tuple[TAccount, TAccount, TAccount]) -> SimpleEntry:
    """Fixture to create a sample simple journal entry."""
    cash_account, _, revenue_account = sample_accounts
    return SimpleEntry(
        debit_account=cash_account,
        credit_account=revenue_account,
        value=100.0,
        date=datetime.date(2023, 10, 1),
        description="Sample Entry",
    )


@pytest.fixture
def sample_compound_entry(sample_accounts: tuple[TAccount, TAccount, TAccount]) -> CompoundEntry:
    """Fixture to create a sample compound journal entry."""
    cash_account, debt_account, revenue_account = sample_accounts
    return CompoundEntry(
        debit_accounts={cash_account: 200.0},
        credit_accounts={
            revenue_account: 100.0,
            debt_account: 100.0,
        },
        date=datetime.date(2023, 10, 1),
        description="Compound Entry",
    )


@pytest.fixture
def sample_journal(sample_journal_entry: SimpleEntry) -> Journal:
    """Fixture to create a sample journal and add a sample journal entry to it."""
    journal = Journal()
    journal.add_entry(sample_journal_entry)
    return journal


def test_add_entry(sample_journal: Journal, sample_journal_entry: SimpleEntry) -> None:
    """Test adding an entry to the journal."""
    assert len(sample_journal.entries) == 1
    sample_journal.add_entry(sample_journal_entry)
    assert len(sample_journal.entries) == 2  # noqa: PLR2004


def test_get_entries_by_date(sample_journal: Journal, sample_journal_entry: SimpleEntry) -> None:
    """Test retrieving entries by date."""
    entries = sample_journal.get_entries_by_date(datetime.date(2023, 10, 1))
    assert len(entries) == 1
    assert entries[0] == sample_journal_entry


def test_get_entries_by_account(
    sample_journal: Journal,
    sample_accounts: tuple[TAccount, TAccount, TAccount],
    sample_journal_entry: SimpleEntry,
) -> None:
    """Test retrieving entries by account."""
    cash_account, _debt_account, _revenue_account = sample_accounts
    entries = sample_journal.get_entries_by_account(cash_account)
    assert len(entries) == 1
    assert entries[0] == sample_journal_entry


def test_get_entries_by_description(sample_journal: Journal, sample_journal_entry: SimpleEntry) -> None:
    """Test retrieving entries by description."""
    entries = sample_journal.get_entries_by_description("Sample Entry")
    assert len(entries) == 1
    assert entries[0] == sample_journal_entry


def test_get_entries_within_date_range(sample_journal: Journal, sample_journal_entry: SimpleEntry) -> None:
    """Test retrieving entries within a date range."""
    entries = sample_journal.get_entries_within_date_range(datetime.date(2023, 9, 30), datetime.date(2023, 10, 2))
    assert len(entries) == 1
    assert entries[0] == sample_journal_entry


def test_remove_entry(sample_journal: Journal, sample_journal_entry: SimpleEntry) -> None:
    """Test removing an entry from the journal."""
    sample_journal.remove_entry(sample_journal_entry)
    assert len(sample_journal.entries) == 0


def test_compound_entry_total_debits(sample_compound_entry: CompoundEntry) -> None:
    """Test calculating the total debits of a compound entry."""
    assert sample_compound_entry.total_debits() == 200.0  # noqa: PLR2004


def test_compound_entry_total_credits(sample_compound_entry: CompoundEntry) -> None:
    """Test calculating the total credits of a compound entry."""
    assert sample_compound_entry.total_credits() == 200.0  # noqa: PLR2004


def test_compound_entry_is_balanced(sample_compound_entry: CompoundEntry) -> None:
    """Test checking if a compound entry is balanced."""
    assert sample_compound_entry.is_balanced()


def test_compound_entry_not_balanced_error(sample_accounts: tuple[TAccount, TAccount, TAccount]) -> None:
    """Test raising an error when a compound entry is not balanced."""
    cash_account, _debt_account, revenue_account = sample_accounts
    with pytest.raises(ValueError):  # noqa: PT011
        CompoundEntry(
            debit_accounts={cash_account: 150.0},
            credit_accounts={revenue_account: 100.0},
            date=datetime.date(2023, 10, 1),
            description="Unbalanced Entry",
        )


def test_compound_entry_involves_account(
    sample_compound_entry: CompoundEntry,
    sample_accounts: tuple[TAccount, TAccount, TAccount],
) -> None:
    """Test checking if a compound entry involves a specific account."""
    cash_account, debt_account, revenue_account = sample_accounts
    assert sample_compound_entry.involves_account(cash_account)
    assert sample_compound_entry.involves_account(debt_account)
    assert sample_compound_entry.involves_account(revenue_account)


def test_add_compound_entry(sample_journal: Journal, sample_compound_entry: CompoundEntry) -> None:
    """Test adding a compound entry to the journal."""
    sample_journal.add_entry(sample_compound_entry)
    assert len(sample_journal.entries) == 2  # noqa: PLR2004
    assert sample_journal.entries[1] == sample_compound_entry


# --- Tests for reversed() ---


def test_simple_entry_reversed(sample_accounts: tuple[TAccount, TAccount, TAccount]) -> None:
    """Test that reversed() swaps debit and credit accounts on a SimpleEntry."""
    cash_account, _debt_account, revenue_account = sample_accounts
    entry = SimpleEntry(
        debit_account=cash_account,
        credit_account=revenue_account,
        value=250.0,
        date=datetime.date(2024, 1, 15),
        description="Original entry",
    )
    rev = entry.reversed()

    assert rev.debit_account is revenue_account
    assert rev.credit_account is cash_account
    assert rev.value == 250.0  # noqa: PLR2004
    assert rev.date == datetime.date(2024, 1, 15)
    assert "Reversal" in rev.description


def test_compound_entry_reversed(sample_accounts: tuple[TAccount, TAccount, TAccount]) -> None:
    """Test that reversed() swaps debit and credit dicts on a CompoundEntry."""
    cash_account, debt_account, revenue_account = sample_accounts
    entry = CompoundEntry(
        debit_accounts={cash_account: 300.0},
        credit_accounts={revenue_account: 200.0, debt_account: 100.0},
        date=datetime.date(2024, 2, 20),
        description="Original compound",
    )
    rev = entry.reversed()

    assert rev.debit_accounts == {revenue_account: 200.0, debt_account: 100.0}
    assert rev.credit_accounts == {cash_account: 300.0}
    assert rev.date == datetime.date(2024, 2, 20)
    assert "Reversal" in rev.description
    assert rev.is_balanced()


if __name__ == "__main__":
    pytest.main([__file__])
