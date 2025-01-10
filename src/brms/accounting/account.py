from collections.abc import Generator
from dataclasses import dataclass, field
from enum import Enum
from itertools import chain
from typing import Optional

from brms.utils import Observable, Observer


class AccountNormalBalance(Enum):
    """The normal balance of an account or the preferred type of net balance that it should have."""

    DEBIT_NORMAL = "Debit normal"
    CREDIT_NORMAL = "Credit normal"


class AccountType(Enum):
    """Types of accounts."""

    ASSET = "Asset"
    LIABILITY = "Liability"
    EQUITY = "Equity"
    INCOME = "Income"
    EXPENSE = "Expense"

    @staticmethod
    def get_normal_balance(account_type: "AccountType", *, contra_account: bool = False) -> AccountNormalBalance:
        """Return the normal balance for a given account type."""
        match account_type:
            case AccountType.ASSET | AccountType.EXPENSE:
                return AccountNormalBalance.DEBIT_NORMAL if not contra_account else AccountNormalBalance.CREDIT_NORMAL
            case AccountType.LIABILITY | AccountType.EQUITY | AccountType.INCOME:
                return AccountNormalBalance.CREDIT_NORMAL if not contra_account else AccountNormalBalance.DEBIT_NORMAL
            case _:
                error_message = f"Unknown account type: {account_type}"
                raise ValueError(error_message)


class TAccount(Observable):
    """Base class representing a T-account, which holds amounts on both the debit and credit sides.

    Simple T-account with no sub-accounts.
    """

    def __init__(
        self,
        name: str,
        account_type: AccountType,
        contra_accounts: list["TAccount"] | None = None,
        parent: Optional["TAccount"] = None,
        debit: float = 0.0,
        credit: float = 0.0,
    ) -> None:
        """Initialize a TAccount instance."""
        super().__init__()
        self.name = name
        self.type = account_type
        self.normal_balance = AccountType.get_normal_balance(account_type)
        self.contra_accounts = contra_accounts or []
        self._parent = parent
        self._debit_value = debit
        self._credit_value = credit

    def debit(self, amount: float) -> None:
        """Add debit amount to account."""
        self.debit_value += amount

    def credit(self, amount: float) -> None:
        """Add credit amount to account."""
        self.credit_value += amount

    def is_balanced(self) -> bool:
        """Check if the T-account is balanced."""
        return self.debit_value == self.credit_value

    @property
    def parent(self) -> Optional["TAccount"]:
        """Get the parent account."""
        return self._parent

    @parent.setter
    def parent(self, parent: Optional["TAccount"]) -> None:
        if isinstance(parent, TAccount) and parent.type != self.type:
            error_message = f"Account type mismatch: {parent.type} != {self.type}"
            raise ValueError(error_message)
        self._parent = parent

    @property
    def debit_value(self) -> float:
        """Return the debit value of the account."""
        return self._debit_value

    @debit_value.setter
    def debit_value(self, value: float) -> None:
        self._check_value_setting()
        self._debit_value = value
        self.notify_observers()  # Notify parent (if any) of the value change

    @property
    def credit_value(self) -> float:
        """Return the credit value of the account."""
        return self._credit_value

    @credit_value.setter
    def credit_value(self, value: float) -> None:
        self._check_value_setting()
        self._credit_value = value
        self.notify_observers()  # Notify parent (if any) of the value change

    def is_composite(self) -> bool:
        """Check if the T-account is composite."""
        return False

    def has_sub_account(self) -> bool:
        """Check if the T-account has any sub account."""
        return False

    def balance(self) -> float:
        """Return account balance."""
        match self.normal_balance:
            case AccountNormalBalance.DEBIT_NORMAL:
                return self.debit_value - self.credit_value
            case AccountNormalBalance.CREDIT_NORMAL:
                return self.credit_value - self.debit_value

    def _check_value_setting(self) -> None:
        """Check if a debit/credit value can be set.

        The value of a composite account with sub accounts should be the sum of sub accounts' values.
        """
        if self.is_composite() and self.has_sub_account():
            error_message = "Cannot set value directly on a composite account with sub accounts"
            raise ValueError(error_message)


class CompositeTAccount(TAccount, Observable, Observer):
    """Composite T-account that can hold multiple sub T-accounts."""

    def __init__(
        self,
        name: str,
        account_type: AccountType,
        contra_accounts: list["TAccount"] | None = None,
        parent: Optional["TAccount"] = None,
        debit: float = 0.0,
        credit: float = 0.0,
    ) -> None:
        """Initialize a CompositeTAccount instance."""
        super().__init__(name, account_type, contra_accounts, parent, debit, credit)
        self.sub_accounts: list[TAccount] = []

    def is_composite(self) -> bool:
        """Check if the T-account is composite."""
        return True

    def has_sub_account(self) -> bool:
        """Check if the T-account has any sub account."""
        return len(self.sub_accounts) > 0

    def add(self, account: TAccount) -> None:
        """Add a T-account as a child and observe it."""
        if account.type != self.type:
            error_message = f"Account type mismatch: {account.type} != {self.type}"
            raise ValueError(error_message)
        if not isinstance(account, TAccount):
            error_message = "Account must be an instance of TAccount"
            raise TypeError(error_message)
        self.sub_accounts.append(account)
        account.parent = self
        account.add_observer(self)  # Observe the child
        self.update(account)  # Update value to include the new child

    def remove(self, account: TAccount) -> None:
        """Remove a T-account as a child and stop observing it."""
        self.sub_accounts.remove(account)
        account.parent = None
        account.remove_observer(self)  # Stop observing the child
        self.update(account)  # Update value to exclude the removed child

    def update(self, observable: Observable) -> None:
        """Triggered when a child account notifies of a change."""
        if not isinstance(observable, TAccount):
            error_message = "Observable must be an instance of TAccount"
            raise TypeError(error_message)
        # We cannot use setters directly
        self._debit_value = sum(account.debit_value for account in self.sub_accounts)
        self._credit_value = sum(account.credit_value for account in self.sub_accounts)
        self.notify_observers()  # Notify parent (if any) of the change


@dataclass
class ChartOfAccounts:
    """Represent the chart of accounts."""

    assets: list[TAccount] = field(default_factory=list)
    equities: list[TAccount] = field(default_factory=list)
    liabilities: list[TAccount] = field(default_factory=list)
    income: list[TAccount] = field(default_factory=list)
    expenses: list[TAccount] = field(default_factory=list)

    income_summary_account = TAccount("Income Summary Account", AccountType.INCOME)
    retained_earnings_account = TAccount("Retained Earnings Account", AccountType.EQUITY)

    def all_accounts(self) -> Generator[TAccount, None, None]:
        """Yield all accounts in the chart of accounts."""
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


class ChartOfAccountsBuilder:
    """Builder for creating a ChartOfAccounts instance."""

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

    def add_asset_account(self, account: TAccount) -> "ChartOfAccountsBuilder":
        """Add an asset account to the builder."""
        self._check_account_type(account, AccountType.ASSET)
        self._assets.append(account)
        return self

    def add_equity_account(self, account: TAccount) -> "ChartOfAccountsBuilder":
        """Add an equity account to the builder."""
        self._check_account_type(account, AccountType.EQUITY)
        self._equities.append(account)
        return self

    def add_liability_account(self, account: TAccount) -> "ChartOfAccountsBuilder":
        """Add a liability account to the builder."""
        self._check_account_type(account, AccountType.LIABILITY)
        self._liabilities.append(account)
        return self

    def add_income_account(self, account: TAccount) -> "ChartOfAccountsBuilder":
        """Add an income account to the builder."""
        self._check_account_type(account, AccountType.INCOME)
        self._income.append(account)
        return self

    def add_expense_account(self, account: TAccount) -> "ChartOfAccountsBuilder":
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
