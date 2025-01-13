"""Defines the Ledger class, which represents a ledger in an accounting system."""

import datetime
from dataclasses import dataclass, field

from brms.accounting.account import AccountBalances, AccountNormalBalance, AccountType, ChartOfAccounts, TAccount
from brms.accounting.journal import CompoundEntry, Journal, JournalEntry, SimpleEntry


@dataclass
class Ledger:
    """A class representing a ledger."""

    journal: Journal = field(default_factory=Journal)
    accounts: dict[str, TAccount] = field(default_factory=dict)
    chart_of_accounts: ChartOfAccounts = field(default_factory=ChartOfAccounts)
    date_closed: datetime.date | None = None

    @property
    def income_summary_account(self) -> TAccount:
        """Retrieve the income summary account."""
        return self.chart_of_accounts.income_summary_account

    @property
    def retained_earnings_account(self) -> TAccount:
        """Retrieve the retained earnings account."""
        return self.chart_of_accounts.retained_earnings_account

    def get_account(self, name: str) -> TAccount:
        """Retrieve an account by name."""
        account = self.accounts.get(name, None)
        if account is None:
            error_message = f"Account with name {name} not found"
            raise ValueError(error_message)
        return account

    def get_accounts_by_type(self, account_type: AccountType) -> list[TAccount]:
        """Retrieve all accounts of a given account type."""
        return [account for account in self.accounts.values() if account.type == account_type]

    def post(self, entry: JournalEntry) -> None:
        """Post a journal entry to the ledger."""
        self.journal.add_entry(entry)
        for account, amount in entry.debit_account_value_pairs():
            account.debit(amount)
        for account, amount in entry.credit_account_value_pairs():
            account.credit(amount)

    def add_accounts_from_chart(self, chart: ChartOfAccounts, balances: AccountBalances | None = None) -> None:
        """Add accounts from a ChartOfAccounts to the ledger.

        This method initializes the ledger with accounts from the provided ChartOfAccounts.
        Optionally, it can also set the starting balances for these accounts based on their
        normal balances (debit or credit).
        """
        self.chart_of_accounts = chart
        for account in chart.all_accounts():
            if balances is not None and account in balances:
                match account.normal_balance:
                    case AccountNormalBalance.DEBIT_NORMAL:
                        account.debit_value = balances[account]
                    case AccountNormalBalance.CREDIT_NORMAL:
                        account.credit_value = balances[account]
            self._add_account(account)

    def close_ledger(self, date: datetime.date) -> None:
        """Close the ledger at the end of an accounting period."""
        self.close_contra_accounts(date)
        self.close_income_and_expense_accounts(date)
        self.close_income_summary_account(date)

    def account_balances(self) -> AccountBalances:
        """Retrieve the balances of all accounts."""
        return AccountBalances({account: account.balance() for account in self.accounts.values()})

    def _add_account(self, account: TAccount) -> None:
        """Add an account to the ledger."""
        if account.name in self.accounts:
            error_message = f"An account with the same name {account.name} already exists"
            raise KeyError(error_message)
        self.accounts[account.name] = account

    def close_contra_accounts(self, date: datetime.date) -> None:
        """Close contra income and contra expense accounts to income summary account."""
        self.date_closed = date
        for account in self.accounts.values():
            for contra in account.contra_accounts:
                self.post(self.generate_closing_entry(contra, date))

    def close_income_and_expense_accounts(self, date: datetime.date) -> None:
        """Close all income and expense accounts."""
        self.date_closed = date
        for account in self.accounts.values():
            if not account.is_contra_account and account.type in (AccountType.INCOME, AccountType.EXPENSE):
                self.post(self.generate_closing_entry(account, date))

    def close_income_summary_account(self, date: datetime.date) -> None:
        """Close the Income Summary account."""
        self.date_closed = date
        income_summary = self.income_summary_account
        retained_earnings = self.retained_earnings_account
        self.post(
            SimpleEntry(
                debit_account=income_summary,
                credit_account=retained_earnings,
                value=income_summary.balance(),
                date=date,
                description="Closing Income Summary account to retained earnings account",
            ),
        )

    def generate_closing_entry(self, account: TAccount, date: datetime.date) -> CompoundEntry:
        """Generate a closing entry for a given account at a specific date."""
        isa = {self.income_summary_account: account.balance()}
        act = (
            {sub: sub.balance() for sub in account.sub_accounts}
            if account.has_sub_account()
            else {account: account.balance()}
        )

        match account.type:
            case AccountType.INCOME:
                return CompoundEntry(
                    debit_accounts=isa if account.is_contra_account else act,
                    credit_accounts=act if account.is_contra_account else isa,
                    date=date,
                    description=f"Closing income account: {account.name}",
                )
            case AccountType.EXPENSE:
                return CompoundEntry(
                    debit_accounts=act if account.is_contra_account else isa,
                    credit_accounts=isa if account.is_contra_account else act,
                    date=date,
                    description=f"Closing expense account: {account.name}",
                )
            case _:
                error_message = f"Unsupported account type: {account.type}"
                raise ValueError(error_message)
