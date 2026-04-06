"""Journal entries and journal for recording accounting transactions."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import datetime
    from collections.abc import Iterator

    from brms.core.models.accounting.accounts import TAccount


class JournalEntry(ABC):
    """Abstract base class for a journal entry."""

    debit_accounts: dict[TAccount, float]
    credit_accounts: dict[TAccount, float]
    date: datetime.date | None
    description: str

    @abstractmethod
    def involves_account(self, account: TAccount) -> bool:
        """Check if the journal entry involves a specific account."""

    @abstractmethod
    def reversed(self) -> JournalEntry:
        """Return a new entry with debits and credits swapped (for step-back)."""

    def debit_account_value_pairs(self) -> Iterator[tuple[TAccount, float]]:
        """Return an iterator over debit account and value pairs."""
        yield from self.debit_accounts.items()

    def credit_account_value_pairs(self) -> Iterator[tuple[TAccount, float]]:
        """Return an iterator over credit account and value pairs."""
        yield from self.credit_accounts.items()


@dataclass
class SimpleEntry(JournalEntry):
    """A simple journal entry affecting exactly two accounts.

    Example: Receiving a $10,000 deposit::

        +----------------------------------------------+
        | Date: 2024-01-15                             |
        | Description: Customer deposit received       |
        +----------------------------------------------+
        | Debit:  Cash ..................... $10,000    |
        | Credit: Deposits ................ $10,000    |
        +----------------------------------------------+
    """

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

    def reversed(self) -> SimpleEntry:
        """Return a new SimpleEntry with debit and credit accounts swapped."""
        return SimpleEntry(
            debit_account=self.credit_account,
            credit_account=self.debit_account,
            value=self.value,
            date=self.date,
            description=f"Reversal: {self.description}",
        )


@dataclass
class CompoundEntry(JournalEntry):
    """A compound journal entry that can affect multiple accounts.

    Used when a transaction touches more than two accounts. The total
    debits must equal total credits (validated on creation).

    Example: Closing a trading income account with sub-accounts::

        +----------------------------------------------+
        | Description: Closing Trading Income          |
        +----------------------------------------------+
        | Debit:  Unrealized Gain ......... $5,000     |
        | Debit:  Realized Gain ........... $3,000     |
        | Credit: Income Summary .......... $6,000     |
        | Credit: Unrealized Loss ......... $2,000     |
        +----------------------------------------------+
    """

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
        tolerance = 1e-6
        return abs(self.total_debits() - self.total_credits()) < tolerance

    def involves_account(self, account: TAccount) -> bool:
        """Check if the journal entry involves a specific account."""
        return account in self.debit_accounts or account in self.credit_accounts

    def reversed(self) -> CompoundEntry:
        """Return a new CompoundEntry with debit and credit accounts swapped."""
        return CompoundEntry(
            debit_accounts=dict(self.credit_accounts),
            credit_accounts=dict(self.debit_accounts),
            date=self.date,
            description=f"Reversal: {self.description}",
        )


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
