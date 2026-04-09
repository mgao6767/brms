"""Chart of accounts: organizes all accounts by category."""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import chain
from typing import TYPE_CHECKING

from brms.core.models.accounting.accounts import AccountType, TAccount

if TYPE_CHECKING:
    from collections.abc import Generator


class IncomeSummaryAccount(TAccount):
    """Represent the income summary account.

    A temporary account used during period-end closing. All income and expense
    account balances are transferred here, and the net result is then closed
    to Retained Earnings.
    """

    def __init__(self) -> None:
        """Initialize an IncomeSummaryAccount instance."""
        super().__init__("Income Summary Account", AccountType.INCOME, is_temporary_account=True)


class RetainedEarningsAccount(TAccount):
    """Represent the retained earnings account.

    Accumulated net income that has not been distributed. During period-end
    closing, the Income Summary balance is transferred here.
    """

    def __init__(self) -> None:
        """Initialize a RetainedEarningsAccount instance."""
        super().__init__("Retained Earnings", AccountType.EQUITY)


@dataclass
class ChartOfAccounts:
    """A chart of accounts organizes all accounts by category.

    ::

        +----------------------------------------------+
        |              Chart of Accounts                |
        +----------------------------------------------+
        | Assets        | What the entity owns          |
        | Liabilities   | What the entity owes          |
        | Equity        | Owner's residual interest     |
        | Income        | Revenue earned (temporary)    |
        | Expenses      | Costs incurred (temporary)    |
        +----------------------------------------------+
        | Accounting equation:                          |
        |   Assets = Liabilities + Equity               |
        |                                               |
        | At period end, Income and Expenses close to   |
        | Retained Earnings (Equity) via Income Summary |
        +----------------------------------------------+
    """

    assets: list[TAccount] = field(default_factory=list)
    equities: list[TAccount] = field(default_factory=list)
    liabilities: list[TAccount] = field(default_factory=list)
    income: list[TAccount] = field(default_factory=list)
    expenses: list[TAccount] = field(default_factory=list)

    income_summary_account: IncomeSummaryAccount = field(default_factory=IncomeSummaryAccount)
    retained_earnings_account: RetainedEarningsAccount = field(default_factory=RetainedEarningsAccount)

    def __iter__(self) -> Generator[TAccount, None, None]:
        """Yield top-level accounts and their contra accounts.

        Composite accounts are yielded as single entries (not expanded).
        Use :meth:`all_accounts` to recursively include sub-accounts.
        """
        all_accounts = chain(
            self.assets,
            self.equities,
            self.liabilities,
            self.income,
            self.expenses,
        )
        for account in all_accounts:
            yield account
            yield from account.contra_accounts
        yield self.income_summary_account
        yield self.retained_earnings_account

    def all_accounts(self) -> Generator[TAccount, None, None]:
        """Yield every account including nested sub-accounts (depth-first).

        Unlike ``__iter__``, this expands composite accounts so that both the
        composite and all of its descendants are yielded.  Useful for lookups
        by name when the target may be a sub-account.
        """
        all_accounts = chain(
            self.assets,
            self.equities,
            self.liabilities,
            self.income,
            self.expenses,
        )
        for account in all_accounts:
            yield from self._walk(account)
            for contra in account.contra_accounts:
                yield from self._walk(contra)
        yield self.income_summary_account
        yield self.retained_earnings_account

    @staticmethod
    def _walk(account: TAccount) -> Generator[TAccount, None, None]:
        """Yield *account* and all its descendants (depth-first)."""
        yield account
        for child in account.sub_accounts:
            yield from ChartOfAccounts._walk(child)


class ChartOfAccountsBuilder:
    """Builder for creating a ChartOfAccounts instance.

    Usage::

        coa = (
            ChartOfAccountsBuilder()
            .add_asset_account(cash)
            .add_liability_account(deposits)
            .add_equity_account(equity)
            .add_income_account(interest_income)
            .add_expense_account(interest_expense)
            .build()
        )
    """

    def __init__(self) -> None:
        """Initialize a ChartOfAccountsBuilder instance."""
        self._assets: list[TAccount] = []
        self._equities: list[TAccount] = []
        self._liabilities: list[TAccount] = []
        self._income: list[TAccount] = []
        self._expenses: list[TAccount] = []

    def _check_account_type(self, account: TAccount, target_account_type: AccountType) -> None:
        if account.type != target_account_type:
            error_message = f"Account type mismatch: {account.type} != {target_account_type}"
            raise ValueError(error_message)

    def add_asset_account(self, account: TAccount) -> ChartOfAccountsBuilder:
        """Add an asset account to the builder."""
        self._check_account_type(account, AccountType.ASSET)
        self._assets.append(account)
        return self

    def add_equity_account(self, account: TAccount) -> ChartOfAccountsBuilder:
        """Add an equity account to the builder."""
        self._check_account_type(account, AccountType.EQUITY)
        self._equities.append(account)
        return self

    def add_liability_account(self, account: TAccount) -> ChartOfAccountsBuilder:
        """Add a liability account to the builder."""
        self._check_account_type(account, AccountType.LIABILITY)
        self._liabilities.append(account)
        return self

    def add_income_account(self, account: TAccount) -> ChartOfAccountsBuilder:
        """Add an income account to the builder."""
        self._check_account_type(account, AccountType.INCOME)
        self._income.append(account)
        return self

    def add_expense_account(self, account: TAccount) -> ChartOfAccountsBuilder:
        """Add an expense account to the builder."""
        self._check_account_type(account, AccountType.EXPENSE)
        self._expenses.append(account)
        return self

    def build(self) -> ChartOfAccounts:
        """Build and return a ChartOfAccounts instance."""
        return ChartOfAccounts(
            assets=self._assets,
            equities=self._equities,
            liabilities=self._liabilities,
            income=self._income,
            expenses=self._expenses,
        )
