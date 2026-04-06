"""General ledger: posts journal entries to accounts and closes the books at period end.

The ledger is the core of the double-entry bookkeeping system.  It holds a
:class:`ChartOfAccounts` (the accounts) and a :class:`Journal` (the record of
all entries).  Posting an entry simultaneously records it in the journal and
updates the affected T-account balances.

Posting flow::

    JournalEntry ──> Ledger.post()
                       ├── journal.add_entry(entry)    (audit trail)
                       ├── account.debit(amount)       (for each debit leg)
                       └── account.credit(amount)      (for each credit leg)

Period-end closing sequence::

    1. close_contra_accounts()
       Contra income/expense balances are netted against their parent accounts.

    2. close_income_and_expense_accounts()
       All income and expense account balances transfer to Income Summary.

    3. close_income_summary_account()
       Income Summary balance transfers to Retained Earnings.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import datetime

from brms.core.models.accounting.accounts import (
    AccountBalances,
    AccountNormalBalance,
    AccountType,
    TAccount,
)
from brms.core.models.accounting.chart_of_accounts import ChartOfAccounts
from brms.core.models.accounting.journal import CompoundEntry, Journal, JournalEntry, SimpleEntry


@dataclass
class Ledger:
    """The general ledger.

    Attributes:
        chart_of_accounts: The chart of accounts containing all T-accounts.
        journal: The journal recording every posted entry.
        date_closed: The date of the most recent period-end close, or ``None``.
    """

    chart_of_accounts: ChartOfAccounts
    journal: Journal = field(default_factory=Journal)
    date_closed: datetime.date | None = None

    # ------------------------------------------------------------------
    # Deep copy
    # ------------------------------------------------------------------

    def __deepcopy__(self, memo: dict[int, Any]) -> Ledger:
        """Create a deep copy with independent accounts but a shared journal.

        The journal is shared (not copied) to avoid issues with QuantLib's
        SWIG objects that cannot be pickled.  The chart of accounts is fully
        deep-copied so that account balances are independent.
        """
        return Ledger(
            chart_of_accounts=copy.deepcopy(self.chart_of_accounts, memo),
            journal=self.journal,
            date_closed=copy.deepcopy(self.date_closed, memo),
        )

    # ------------------------------------------------------------------
    # Posting
    # ------------------------------------------------------------------

    def post(self, entry: JournalEntry) -> None:
        """Post a journal entry: record it and update account balances.

        For each debit leg, the corresponding account's debit side increases.
        For each credit leg, the corresponding account's credit side increases.
        The entry is appended to the journal for audit purposes.
        """
        self.journal.add_entry(entry)
        for account, amount in entry.debit_account_value_pairs():
            account.debit(amount)
        for account, amount in entry.credit_account_value_pairs():
            account.credit(amount)

    # ------------------------------------------------------------------
    # Balance queries
    # ------------------------------------------------------------------

    def get_account_balances(self) -> AccountBalances:
        """Return a snapshot of all account balances."""
        return AccountBalances({account: account.balance() for account in self.chart_of_accounts})

    def set_account_balances(self, balances: AccountBalances) -> None:
        """Set opening balances directly on accounts.

        This bypasses the journal (no entry is recorded) and should only be
        used for initial setup, never during normal operation.

        Each balance is applied to the account's normal side:
        debit-normal accounts get a debit, credit-normal accounts get a credit.
        """
        for account, balance in balances.items():
            if account.normal_balance == AccountNormalBalance.DEBIT_NORMAL:
                account.debit_value = balance
            else:
                account.credit_value = balance

    def get_accounts_by_type(self, account_type: AccountType) -> list[TAccount]:
        """Return all accounts matching the given type."""
        return [acct for acct in self.chart_of_accounts if acct.type == account_type]

    # ------------------------------------------------------------------
    # Period-end closing
    # ------------------------------------------------------------------

    def close_ledger(self, date: datetime.date) -> None:
        """Run the full period-end closing sequence.

        1. Net contra accounts against their parents.
        2. Transfer income/expense balances to Income Summary.
        3. Transfer Income Summary to Retained Earnings.
        """
        self.close_contra_accounts(date)
        self.close_income_and_expense_accounts(date)
        self.close_income_summary_account(date)

    def close_contra_accounts(self, date: datetime.date) -> None:
        """Net contra account balances against their parent income/expense accounts.

        For an income account with contra expenses (e.g., Trading Income with
        Unrealized Trading Loss), this posts an entry that zeroes the contra
        balances and reduces the parent's balance by the same amount.
        """
        self.date_closed = date
        for account in self.chart_of_accounts:
            if not account.has_contra_account():
                continue
            if account.type not in (AccountType.INCOME, AccountType.EXPENSE):
                continue

            contra_total = sum(contra.balance() for contra in account.contra_accounts)
            if contra_total == 0:
                continue

            if account.type == AccountType.INCOME:
                debit_accounts = {account: contra_total}
                credit_accounts = {contra: contra.balance() for contra in account.contra_accounts}
            else:
                debit_accounts = {contra: contra.balance() for contra in account.contra_accounts}
                credit_accounts = {account: contra_total}

            self.post(CompoundEntry(
                debit_accounts=debit_accounts,
                credit_accounts=credit_accounts,
                date=date,
                description=f"Close contra accounts of {account.name}",
            ))

    def close_income_and_expense_accounts(self, date: datetime.date) -> None:
        """Transfer all income and expense balances to Income Summary.

        Skips contra accounts (already closed) and the Income Summary account itself.
        """
        self.date_closed = date
        income_summary = self.chart_of_accounts.income_summary_account

        for account in self.chart_of_accounts:
            if account.is_contra_account:
                continue
            if account.type not in (AccountType.INCOME, AccountType.EXPENSE):
                continue
            if account is income_summary:
                continue
            if account.balance() == 0:
                continue

            self.post(self._make_closing_entry(account, income_summary, date))

    def close_income_summary_account(self, date: datetime.date) -> None:
        """Transfer the Income Summary balance to Retained Earnings."""
        self.date_closed = date
        income_summary = self.chart_of_accounts.income_summary_account
        retained_earnings = self.chart_of_accounts.retained_earnings_account

        balance = income_summary.balance()
        if balance == 0:
            return

        self.post(SimpleEntry(
            debit_account=income_summary,
            credit_account=retained_earnings,
            value=balance,
            date=date,
            description="Close Income Summary to Retained Earnings",
        ))

    # ------------------------------------------------------------------
    # Closing helpers
    # ------------------------------------------------------------------

    def _make_closing_entry(
        self, account: TAccount, income_summary: TAccount, date: datetime.date,
    ) -> CompoundEntry:
        """Build a closing entry that transfers *account*'s balance to Income Summary.

        Handles three cases:
        - Simple income account: debit the account, credit Income Summary.
        - Simple expense account: debit Income Summary, credit the account.
        - Composite income account with mixed sub-types (e.g., Trading Income
          containing both gain/income and loss/expense sub-accounts):
          The net balance is transferred, with income subs debited and expense
          subs credited (or vice versa if net loss).
        """
        if account.type == AccountType.EXPENSE:
            return self._close_expense_account(account, income_summary, date)

        if account.type == AccountType.INCOME:
            return self._close_income_account(account, income_summary, date)

        msg = f"Cannot close account of type {account.type} — only INCOME and EXPENSE are closable"
        raise ValueError(msg)

    def _close_expense_account(
        self, account: TAccount, income_summary: TAccount, date: datetime.date,
    ) -> CompoundEntry:
        """Close an expense account: debit ISA, credit the expense (or its subs)."""
        account_entries = (
            {sub: sub.balance() for sub in account.sub_accounts}
            if account.has_sub_account()
            else {account: account.balance()}
        )
        return CompoundEntry(
            debit_accounts={income_summary: abs(account.balance())},
            credit_accounts=account_entries,
            date=date,
            description=f"Close expense account: {account.name}",
        )

    def _close_income_account(
        self, account: TAccount, income_summary: TAccount, date: datetime.date,
    ) -> CompoundEntry:
        """Close an income account: debit the income (or its subs), credit ISA.

        Composite income accounts may contain expense-type sub-accounts
        (e.g., Trading Income has Unrealized Trading Loss).  The entry must
        balance: income subs are debited, expense subs are credited, and the
        net goes to Income Summary.
        """
        if account.has_sub_account():
            income_subs = {sub: sub.balance() for sub in account.sub_accounts if sub.type == AccountType.INCOME}
            expense_subs = {sub: sub.balance() for sub in account.sub_accounts if sub.type == AccountType.EXPENSE}
        else:
            income_subs = {account: account.balance()}
            expense_subs = {}

        net_balance = account.balance()
        isa_amount = abs(net_balance)

        if net_balance >= 0:
            # Net gain: debit income subs, credit ISA + expense subs
            return CompoundEntry(
                debit_accounts=income_subs,
                credit_accounts={income_summary: isa_amount, **expense_subs},
                date=date,
                description=f"Close income account: {account.name}",
            )

        # Net loss: debit ISA + income subs, credit expense subs
        return CompoundEntry(
            debit_accounts={income_summary: isa_amount, **income_subs},
            credit_accounts=expense_subs,
            date=date,
            description=f"Close income account: {account.name} (net loss)",
        )
