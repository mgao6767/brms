import datetime
from dataclasses import dataclass, field

from brms.accounting.account import AccountType, ChartOfAccounts, TAccount
from brms.accounting.journal import Journal, JournalEntry, SimpleEntry


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

    def close_ledger(self, date: datetime.date) -> None:
        """Close the ledger at the end of an accounting period."""
        self.close_income_accounts(date)
        self.close_expense_accounts(date)
        self.close_income_summary(date)

    def close_income_accounts(self, date: datetime.date) -> None:
        """Close all income accounts including contra accounts."""
        income_summary = self.get_income_summary_account()
        for name, account in self.accounts.items():
            if account.type == AccountType.INCOME:
                self.post(
                    SimpleEntry(
                        debit_account=account,
                        credit_account=income_summary,
                        value=account.balance(),
                        date=date,
                        description=f"Closing income account: {name}",
                    ),
                )
                for contra in account.contra_accounts:
                    self.post(
                        SimpleEntry(
                            debit_account=income_summary,
                            credit_account=contra,
                            value=contra.balance(),
                            date=date,
                            description=f"Closing contra income account: {contra.name}",
                        ),
                    )

    def close_expense_accounts(self, date: datetime.date) -> None:
        """Close all expense accounts including contra accounts."""
        income_summary = self.get_income_summary_account()
        for name, account in self.accounts.items():
            if account.type == AccountType.EXPENSE:
                self.post(
                    SimpleEntry(
                        debit_account=income_summary,
                        credit_account=account,
                        value=account.balance(),
                        date=date,
                        description=f"Closing expense account: {name}",
                    ),
                )
                for contra in account.contra_accounts:
                    self.post(
                        SimpleEntry(
                            debit_account=contra,
                            credit_account=income_summary,
                            value=contra.balance(),
                            date=date,
                            description=f"Closing contra expense account: {contra.name}",
                        ),
                    )

    def close_income_summary(self, date: datetime.date) -> None:
        """Close the Income Summary account."""
        income_summary = self.get_income_summary_account()
        retained_earnings = self.get_retained_earnings_account()
        self.post(
            SimpleEntry(
                debit_account=income_summary,
                credit_account=retained_earnings,
                value=income_summary.balance(),
                date=date,
                description="Closing Income Summary account to retained earnings account",
            ),
        )

    def get_income_summary_account(self) -> TAccount:
        # TODO: should not use the account name to get ISA
        return self.get_account("Income Summary Account")

    def get_retained_earnings_account(self) -> TAccount:
        # TODO: should not use the account name to get REA
        return self.get_account("Retained Earnings Account")
