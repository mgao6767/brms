"""Module for accounting journal and entries."""

import datetime
from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass, field

from tabulate import tabulate

from brms.accounting.account import TAccount


class JournalEntry(ABC):
    """Abstract base class for a journal entry."""

    debit_accounts: dict[TAccount, float]
    credit_accounts: dict[TAccount, float]
    date: datetime.date | None
    description: str

    @abstractmethod
    def involves_account(self, account: TAccount) -> bool:
        """Check if the journal entry involves a specific account."""

    def debit_account_value_pairs(self) -> Iterator[tuple[TAccount, float]]:
        """Return an iterator over debit account and value pairs."""
        yield from self.debit_accounts.items()

    def credit_account_value_pairs(self) -> Iterator[tuple[TAccount, float]]:
        """Return an iterator over credit account and value pairs."""
        yield from self.credit_accounts.items()


@dataclass
class SimpleEntry(JournalEntry):
    """Represent a simple journal entry with debit and credit accounts and a value."""

    debit_account: TAccount
    credit_account: TAccount
    value: float
    date: datetime.date | None = None
    description: str = ""

    def __post_init__(self) -> None:
        """Post-initialization processing to conform the protocol."""
        self.debit_accounts: dict[TAccount, float] = {self.debit_account: self.value}
        self.credit_accounts: dict[TAccount, float] = {self.credit_account: self.value}

    def involves_account(self, account: TAccount) -> bool:
        """Check if the journal entry involves a specific account."""
        return account in {self.debit_account, self.credit_account}

    def to_html(self) -> str:
        """Return a string representation of the simple journal entry."""
        data = [
            ["Dr.", self.debit_account.name, self.value],
            ["Cr.", self.credit_account.name, self.value],
        ]
        return tabulate(data, tablefmt="html", numalign="right", floatfmt=".2f", maxcolwidths=[None, 50])


@dataclass
class CompoundEntry(JournalEntry):
    """Represent a compound journal entry that can affect multiple accounts."""

    debit_accounts: dict[TAccount, float]
    credit_accounts: dict[TAccount, float]
    date: datetime.date | None = None
    description: str = ""

    def __post_init__(self) -> None:
        """Post-initialization processing to validate the compound journal entry."""
        self.validate()

    def validate(self) -> None:
        """Assert sum of debit entries equals sum of credit entries."""
        if not self.is_balanced():
            error_message = "Compound journal entry is not balanced"
            raise ValueError(error_message)

    def total_debits(self) -> float:
        """Calculate the total debits for the compound entry."""
        return sum(self.debit_accounts.values())

    def total_credits(self) -> float:
        """Calculate the total credits for the compound entry."""
        return sum(self.credit_accounts.values())

    def is_balanced(self) -> bool:
        """Check if the compound entry is balanced.

        Using 1e-6 as a tolerance level to account for floating-point inaccuracies.
        """
        return abs(self.total_debits() - self.total_credits()) < 1e-6

    def involves_account(self, account: TAccount) -> bool:
        """Check if the journal entry involves a specific account."""
        return account in self.debit_accounts or account in self.credit_accounts

    def to_html(self) -> str:
        """Return a string representation of the simple journal entry."""
        data = []
        for account, value in self.debit_accounts.items():
            data.append(["Dr.", account.name, value])
        for account, value in self.credit_accounts.items():
            data.append(["Cr.", account.name, value])
        return tabulate(data, tablefmt="html", numalign="right", floatfmt=".2f", maxcolwidths=[None, 50])


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
        return [entry for entry in self.entries if entry.involves_account(account)]

    def get_entries_by_description(self, description: str) -> list[JournalEntry]:
        """Get all journal entries matching a specific description."""
        return [entry for entry in self.entries if description in entry.description]

    def get_entries_within_date_range(self, start_date: datetime.date, end_date: datetime.date) -> list[JournalEntry]:
        """Get all journal entries within a specific date range."""
        return [entry for entry in self.entries if entry.date is not None and start_date <= entry.date <= end_date]

    def remove_entry(self, entry: JournalEntry) -> None:
        """Remove a specific journal entry."""
        self.entries.remove(entry)
