import datetime
from dataclasses import dataclass, field

from brms.accounting.account import TAccount


@dataclass
class JournalEntry:
    """Represent a journal entry with debit and credit accounts and a value."""

    debit_account: TAccount
    credit_account: TAccount
    value: float
    date: datetime.date | None = None
    description: str = ""


@dataclass
class Journal:
    """Class to record all journal entries."""

    entries: list[JournalEntry] = field(default_factory=list)

    def add_entry(self, entry: JournalEntry) -> None:
        """Add a journal entry to the journal."""
        self.entries.append(entry)

    def get_entries_by_date(self, date: datetime.date) -> list[JournalEntry]:
        """Get all journal entries for a specific date."""
        return [entry for entry in self.entries if entry.date == date]

    def get_entries_by_account(self, account: TAccount) -> list[JournalEntry]:
        """Get all journal entries involving a specific account."""
        return [entry for entry in self.entries if account in {entry.debit_account, entry.credit_account}]

    def get_entries_by_description(self, description: str) -> list[JournalEntry]:
        """Get all journal entries matching a specific description."""
        return [entry for entry in self.entries if description in entry.description]

    def get_entries_within_date_range(self, start_date: datetime.date, end_date: datetime.date) -> list[JournalEntry]:
        """Get all journal entries within a specific date range."""
        return [entry for entry in self.entries if start_date <= entry.date <= end_date]

    def remove_entry(self, entry: JournalEntry) -> None:
        """Remove a specific journal entry."""
        self.entries.remove(entry)
