import datetime

import pytest

from brms.accounting.account import AccountType, TAccount
from brms.accounting.journal import Journal, JournalEntry


@pytest.fixture
def sample_accounts():
    debit_account = TAccount("Cash", AccountType.ASSET)
    credit_account = TAccount("Revenue", AccountType.INCOME)
    return debit_account, credit_account


@pytest.fixture
def sample_journal_entry(sample_accounts):
    debit_account, credit_account = sample_accounts
    return JournalEntry(
        debit_account=debit_account,
        credit_account=credit_account,
        value=100.0,
        date=datetime.date(2023, 10, 1),
        description="Sample Entry",
    )


@pytest.fixture
def sample_journal(sample_journal_entry):
    journal = Journal()
    journal.add_entry(sample_journal_entry)
    return journal


def test_add_entry(sample_journal, sample_journal_entry):
    assert len(sample_journal.entries) == 1
    sample_journal.add_entry(sample_journal_entry)
    assert len(sample_journal.entries) == 2


def test_get_entries_by_date(sample_journal, sample_journal_entry):
    entries = sample_journal.get_entries_by_date(datetime.date(2023, 10, 1))
    assert len(entries) == 1
    assert entries[0] == sample_journal_entry


def test_get_entries_by_account(sample_journal, sample_accounts, sample_journal_entry):
    debit_account, credit_account = sample_accounts
    entries = sample_journal.get_entries_by_account(debit_account)
    assert len(entries) == 1
    assert entries[0] == sample_journal_entry


def test_get_entries_by_description(sample_journal, sample_journal_entry):
    entries = sample_journal.get_entries_by_description("Sample Entry")
    assert len(entries) == 1
    assert entries[0] == sample_journal_entry


def test_get_entries_within_date_range(sample_journal, sample_journal_entry):
    entries = sample_journal.get_entries_within_date_range(datetime.date(2023, 9, 30), datetime.date(2023, 10, 2))
    assert len(entries) == 1
    assert entries[0] == sample_journal_entry


def test_remove_entry(sample_journal, sample_journal_entry):
    sample_journal.remove_entry(sample_journal_entry)
    assert len(sample_journal.entries) == 0


if __name__ == "__main__":
    pytest.main([__file__])
