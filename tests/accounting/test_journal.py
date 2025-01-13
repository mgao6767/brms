import datetime

import pytest

from brms.accounting.account import AccountType, TAccount
from brms.accounting.journal import CompoundEntry, Journal, SimpleEntry


@pytest.fixture
def sample_accounts():
    cash_account = TAccount("Cash", AccountType.ASSET)
    debt_account = TAccount("Debt", AccountType.LIABILITY)
    revenue_account = TAccount("Revenue", AccountType.INCOME)
    return cash_account, debt_account, revenue_account


@pytest.fixture
def sample_journal_entry(sample_accounts):
    cash_account, _, revenue_account = sample_accounts
    return SimpleEntry(
        debit_account=cash_account,
        credit_account=revenue_account,
        value=100.0,
        date=datetime.date(2023, 10, 1),
        description="Sample Entry",
    )


@pytest.fixture
def sample_compound_entry(sample_accounts):
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
    cash_account, debt_account, revenue_account = sample_accounts
    entries = sample_journal.get_entries_by_account(cash_account)
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


def test_compound_entry_total_debits(sample_compound_entry):
    assert sample_compound_entry.total_debits() == 200.0


def test_compound_entry_total_credits(sample_compound_entry):
    assert sample_compound_entry.total_credits() == 200.0


def test_compound_entry_is_balanced(sample_compound_entry):
    assert sample_compound_entry.is_balanced()


def test_compound_entry_involves_account(sample_compound_entry, sample_accounts):
    cash_account, debt_account, revenue_account = sample_accounts
    assert sample_compound_entry.involves_account(cash_account)
    assert sample_compound_entry.involves_account(debt_account)
    assert sample_compound_entry.involves_account(revenue_account)


def test_add_compound_entry(sample_journal, sample_compound_entry):
    sample_journal.add_entry(sample_compound_entry)
    assert len(sample_journal.entries) == 2
    assert sample_journal.entries[1] == sample_compound_entry


if __name__ == "__main__":
    pytest.main([__file__])
