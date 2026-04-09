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

            # Collect contra leaf accounts with non-zero balances
            contra_entries: dict[TAccount, float] = {}
            for contra in account.contra_accounts:
                for leaf in contra.posting_accounts():
                    bal = leaf.balance()
                    if bal != 0:
                        contra_entries[leaf] = bal

            contra_total = sum(contra_entries.values())
            if contra_total == 0:
                continue

            # The parent account absorbs the contra total.
            # Use leaves if the parent is composite to avoid direct-set errors.
            parent_entries: dict[TAccount, float] = {}
            parent_leaves = list(account.posting_accounts())
            if len(parent_leaves) == 1:
                parent_entries[parent_leaves[0]] = contra_total
            else:
                # Distribute proportionally across leaves (simplified: put it all on the first leaf)
                # In practice, contra closing usually applies to simple accounts, not composites.
                parent_entries[parent_leaves[0]] = contra_total

            if account.type == AccountType.INCOME:
                debit_accounts = parent_entries
                credit_accounts = contra_entries
            else:
                debit_accounts = contra_entries
                credit_accounts = parent_entries

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

        Works uniformly for income and expense accounts, including composites
        with mixed sub-types (e.g., Trading Income containing both gain and
        loss sub-accounts).

        The entry zeroes every leaf account and absorbs the net into ISA::

            Simple income (balance 5000):
                Debit  Interest Income  5000
                Credit Income Summary   5000

            Simple expense (balance 2000):
                Debit  Income Summary   2000
                Credit Interest Expense 2000

            Composite with mixed subs (net gain 3000):
                Debit  Trading Gain     4000   (income sub)
                Credit Trading Loss     1000   (expense sub)
                Credit Income Summary   3000   (net)
        """
        if account.type not in (AccountType.INCOME, AccountType.EXPENSE):
            msg = f"Cannot close account of type {account.type} — only INCOME and EXPENSE are closable"
            raise ValueError(msg)

        # Collect leaf accounts grouped by their normal side.
        # "debit-normal" accounts (expenses) need to be credited to zero.
        # "credit-normal" accounts (income) need to be debited to zero.
        # Uses leaves() to recurse through any depth of composite nesting.
        to_debit: dict[TAccount, float] = {}  # accounts we will debit (income-type leaves)
        to_credit: dict[TAccount, float] = {}  # accounts we will credit (expense-type leaves)

        for leaf in account.posting_accounts():
            bal = leaf.balance()
            if bal == 0:
                continue
            if leaf.type in (AccountType.INCOME, AccountType.EQUITY):
                # Credit-normal: debit to zero
                to_debit[leaf] = bal
            else:
                # Debit-normal (expense): credit to zero
                to_credit[leaf] = bal

        # ISA absorbs the net. Positive net = credit ISA, negative = debit ISA.
        net = sum(to_debit.values()) - sum(to_credit.values())
        if net >= 0:
            to_credit[income_summary] = net
        else:
            to_debit[income_summary] = abs(net)

        return CompoundEntry(
            debit_accounts=to_debit,
            credit_accounts=to_credit,
            date=date,
            description=f"Close account: {account.name}",
        )
