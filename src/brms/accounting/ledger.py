from dataclasses import dataclass, field

from brms.accounting.account import ChartOfAccounts, TAccount
from brms.accounting.journal import Journal, JournalEntry


@dataclass
class Ledger:
    """A class representing a ledger."""

    journal: Journal = field(default_factory=Journal)
    accounts: dict[str, TAccount] = field(default_factory=dict)

    def add_account(self, account: TAccount) -> None:
        """Add an account to the ledger."""
        if account.name in self.accounts:
            error_message = f"An account with the same name {account.name} already exists"
            raise KeyError(error_message)
        self.accounts[account.name] = account

    def get_account(self, name: str) -> TAccount:
        """Retrieve an account by name."""
        account = self.accounts.get(name, None)
        if account is None:
            error_message = f"Account with name {name} not found"
            raise ValueError(error_message)
        return account

    def post(self, entry: JournalEntry) -> None:
        """Post a journal entry to the ledger."""
        self.journal.add_entry(entry)
        for account, amount in entry.debit_account_value_pairs():
            account.debit(amount)
        for account, amount in entry.credit_account_value_pairs():
            account.credit(amount)

    def add_accounts_from_chart(self, chart: ChartOfAccounts) -> None:
        """Add accounts from a ChartOfAccounts to the ledger."""
        for account in chart.all_accounts():
            self.add_account(account)
