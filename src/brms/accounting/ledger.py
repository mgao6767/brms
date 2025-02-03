"""Module for accounting ledger."""

import copy
import datetime
from dataclasses import dataclass, field

from brms.accounting.account import AccountBalances, AccountNormalBalance, AccountType, ChartOfAccounts, TAccount
from brms.accounting.journal import CompoundEntry, Journal, JournalEntry, SimpleEntry


@dataclass
class Ledger:
    """A class representing a ledger."""

    chart_of_accounts: ChartOfAccounts
    journal: Journal = field(default_factory=Journal)
    date_closed: datetime.date | None = None

    def __deepcopy__(self, memo) -> "Ledger":
        # Somehow in PySide, deepcopy ledger cause TypeError: cannot pickle 'SwigPyObject' object
        # A fix found is not to copy `journal`
        new_obj = Ledger(
            journal=self.journal,  # Don't copy journal
            chart_of_accounts=copy.deepcopy(self.chart_of_accounts, memo),
            date_closed=copy.deepcopy(self.date_closed, memo),
        )
        return new_obj

    @property
    def coa(self) -> ChartOfAccounts:
        """Return the chart of accounts."""
        return self.chart_of_accounts

    def post(self, entry: JournalEntry) -> None:
        """Post a journal entry to the ledger."""
        self.journal.add_entry(entry)
        for account, amount in entry.debit_account_value_pairs():
            account.debit(amount)
        for account, amount in entry.credit_account_value_pairs():
            account.credit(amount)

    def set_account_balances(self, balances: AccountBalances) -> None:
        """Set the starting balances of accounts based on their normal balances (debit or credit)."""
        for account, balance in balances.items():
            match account.normal_balance:
                case AccountNormalBalance.DEBIT_NORMAL:
                    account.debit_value = balance
                case AccountNormalBalance.CREDIT_NORMAL:
                    account.credit_value = balance

    def get_account_balances(self) -> AccountBalances:
        """Retrieve the balances of all accounts."""
        return AccountBalances({account: account.balance() for account in self.chart_of_accounts})

    def get_accounts_by_type(self, account_type: AccountType) -> list[TAccount]:
        """Retrieve all accounts of a given account type."""
        return [account for account in self.chart_of_accounts if account.type == account_type]

    def close_ledger(self, date: datetime.date) -> None:
        """Close the ledger at the end of an accounting period."""
        self.close_contra_accounts(date)
        self.close_income_and_expense_accounts(date)
        self.close_income_summary_account(date)

    def close_contra_accounts(self, date: datetime.date) -> None:
        """Close contra income and contra expense accounts.

        Contra accounts are not closed to ISA, but closed to the original income or expense accounts.
        """
        self.date_closed = date
        for account in self.chart_of_accounts:
            if account.has_contra_account() and account.type in (AccountType.INCOME, AccountType.EXPENSE):
                match account.type:
                    case AccountType.INCOME:
                        _debit_accounts = {account: sum(contra.balance() for contra in account.contra_accounts)}
                        _credit_accounts = {contra: contra.balance() for contra in account.contra_accounts}
                    case AccountType.EXPENSE:
                        _debit_accounts = {contra: contra.balance() for contra in account.contra_accounts}
                        _credit_accounts = {account: sum(contra.balance() for contra in account.contra_accounts)}
                self.post(
                    CompoundEntry(
                        debit_accounts=_debit_accounts,
                        credit_accounts=_credit_accounts,
                        date=date,
                        description=f"Closing contra accounts of {account.name}",
                    ),
                )

    def close_income_and_expense_accounts(self, date: datetime.date) -> None:
        """Close all income and expense accounts."""
        self.date_closed = date
        for account in self.chart_of_accounts:
            if (
                not account.is_contra_account
                and account.type in (AccountType.INCOME, AccountType.EXPENSE)
                and account != self.coa.income_summary_account
            ):
                self.post(self.generate_closing_entry(account, date))

    def close_income_summary_account(self, date: datetime.date) -> None:
        """Close the Income Summary account."""
        self.date_closed = date
        income_summary = self.chart_of_accounts.income_summary_account
        retained_earnings = self.chart_of_accounts.retained_earnings_account
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
        isa = {self.chart_of_accounts.income_summary_account: abs(account.balance())}  # account balance may be negative
        act = (
            {sub: sub.balance() for sub in account.sub_accounts}
            if account.has_sub_account()
            else {account: account.balance()}
        )

        match account.type:
            case AccountType.INCOME:
                # fmt: off
                if account.has_sub_account():
                    income_accounts = {sub: sub.balance() for sub in account.sub_accounts if sub.type == AccountType.INCOME}
                    expense_accounts = {sub: sub.balance() for sub in account.sub_accounts if sub.type == AccountType.EXPENSE}
                else:
                    income_accounts = {account: account.balance()}
                    expense_accounts = {}
                # fmt: on
                if account.balance() >= 0:  # net gain
                    return CompoundEntry(
                        debit_accounts=income_accounts,
                        credit_accounts={**isa, **expense_accounts},
                        date=date,
                        description=f"Closing income account: {account.name}",
                    )
                else:  # net loss
                    return CompoundEntry(
                        debit_accounts={**isa, **income_accounts},
                        credit_accounts=expense_accounts,
                        date=date,
                        description=f"Closing income account: {account.name}",
                    )
            case AccountType.EXPENSE:
                return CompoundEntry(
                    debit_accounts=isa,
                    credit_accounts=act,
                    date=date,
                    description=f"Closing expense account: {account.name}",
                )
            case _:
                error_message = f"Unsupported account type: {account.type}"
                raise ValueError(error_message)
