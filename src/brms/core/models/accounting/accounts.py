"""Generic T-account types and account classifications for double-entry bookkeeping."""

from __future__ import annotations

from collections import UserDict
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Generator


class AccountNormalBalance(Enum):
    """The normal balance of an account or the preferred type of net balance that it should have.

    In double-entry bookkeeping, every account has a "normal" side:

    - **DEBIT_NORMAL**: Asset and Expense accounts normally carry debit balances.
      Debits increase these accounts; credits decrease them.
    - **CREDIT_NORMAL**: Liability, Equity, and Income accounts normally carry
      credit balances. Credits increase these accounts; debits decrease them.
    """

    DEBIT_NORMAL = "Debit normal"
    CREDIT_NORMAL = "Credit normal"


class AccountType(Enum):
    """Types of accounts in the accounting equation.

    The five fundamental account types:

    - **Asset** -- resources owned (debit-normal)
    - **Liability** -- obligations owed (credit-normal)
    - **Equity** -- residual interest (credit-normal)
    - **Income** -- revenue earned (credit-normal, temporary)
    - **Expense** -- costs incurred (debit-normal, temporary)

    Accounting equation: Assets = Liabilities + Equity
    """

    ASSET = "Asset"
    LIABILITY = "Liability"
    EQUITY = "Equity"
    INCOME = "Income"
    EXPENSE = "Expense"

    @staticmethod
    def get_normal_balance(account_type: AccountType, *, contra_account: bool = False) -> AccountNormalBalance:
        """Return the normal balance for a given account type.

        A contra account has the opposite normal balance of its parent account type.
        For example, a contra-asset account has a credit-normal balance.
        """
        match account_type:
            case AccountType.ASSET | AccountType.EXPENSE:
                return AccountNormalBalance.DEBIT_NORMAL if not contra_account else AccountNormalBalance.CREDIT_NORMAL
            case AccountType.LIABILITY | AccountType.EQUITY | AccountType.INCOME:
                return AccountNormalBalance.CREDIT_NORMAL if not contra_account else AccountNormalBalance.DEBIT_NORMAL
            case _:
                error_message = f"Unknown account type: {account_type}"
                raise ValueError(error_message)


class AccountBalances(UserDict["TAccount", float]):
    """A dictionary-like class to hold account balances."""

    @classmethod
    def from_accounts(cls, accounts: list[TAccount]) -> AccountBalances:
        """Create an AccountBalances instance from a list of accounts."""
        balances = cls()
        for account in accounts:
            balances[account] = account.balance()
        return balances


class TAccount:
    """A T-account in double-entry bookkeeping.

    A T-account has two sides: debit (left) and credit (right).
    The normal balance determines which side increases the account value.

    Asset and Expense accounts have DEBIT normal balance::

        +----------------------------------+
        |         Cash (Asset)             |
        +-----------------+----------------+
        |     Debit       |    Credit      |
        |   (increase)    |   (decrease)   |
        +-----------------+----------------+
        |    1,000        |      200       |
        |      500        |                |
        +-----------------+----------------+
        |   Balance: 1,300                 |
        +----------------------------------+

    Liability, Equity, and Income accounts have CREDIT normal balance::

        +----------------------------------+
        |       Deposits (Liability)       |
        +-----------------+----------------+
        |     Debit       |    Credit      |
        |   (decrease)    |   (increase)   |
        +-----------------+----------------+
        |                 |    5,000       |
        |      200        |    1,000       |
        +-----------------+----------------+
        |              Balance: 5,800      |
        +----------------------------------+

    Double-entry principle: every transaction debits one account
    and credits another for the same amount, keeping the books balanced.

    Example: Receiving a $10,000 deposit::

        Cash.debit(10_000)      -- Cash increases
        Deposits.credit(10_000) -- Deposits increases
    """

    def __init__(  # noqa: PLR0913
        self,
        name: str,
        account_type: AccountType,
        contra_accounts: list[TAccount] | None = None,
        parent: TAccount | None = None,
        debit: float = 0.0,
        credit: float = 0.0,
        description: str = "",
        *,
        is_contra_account: bool = False,
        is_temporary_account: bool = False,
    ) -> None:
        """Initialize a TAccount instance."""
        self.name = name
        self.type = account_type
        self.normal_balance = AccountType.get_normal_balance(account_type, contra_account=is_contra_account)
        self.contra_accounts = contra_accounts or []
        self._parent = parent
        self._debit_value = debit
        self._credit_value = credit
        self.description = description
        self.is_contra_account = is_contra_account
        self.is_temporary_account = is_temporary_account

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
    def parent(self) -> TAccount | None:
        """Get the parent account."""
        return self._parent

    @parent.setter
    def parent(self, parent: TAccount | None) -> None:
        """Set the parent account."""
        # Do not require same type because Trading Income contains Gains (income) and Losses (expense)
        self._parent = parent

    @property
    def debit_value(self) -> float:
        """Return the debit value of the account."""
        return self._debit_value

    @debit_value.setter
    def debit_value(self, value: float) -> None:
        self._check_value_setting()
        self._debit_value = value
        self._propagate_to_parent()

    @property
    def credit_value(self) -> float:
        """Return the credit value of the account."""
        return self._credit_value

    @credit_value.setter
    def credit_value(self, value: float) -> None:
        self._check_value_setting()
        self._credit_value = value
        self._propagate_to_parent()

    @property
    def sub_accounts(self) -> Generator[TAccount, None, None]:
        """Return an iterator over sub-accounts."""
        yield from ()

    def is_composite(self) -> bool:
        """Check if the T-account is composite."""
        return False

    def has_sub_account(self) -> bool:
        """Check if the T-account has any sub account."""
        return False

    def has_contra_account(self) -> bool:
        """Check if the T-account has any contra account."""
        return len(self.contra_accounts) > 0

    def leaves(self) -> Generator[TAccount, None, None]:
        """Yield all leaf (non-composite or childless) accounts in the sub-tree.

        For a simple TAccount, yields itself.
        For a CompositeTAccount, recursively yields the leaves of all children.
        This is used by the Ledger when posting closing entries — only leaf
        accounts can be directly debited/credited.
        """
        yield self

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

    def _propagate_to_parent(self) -> None:
        """Propagate value changes to the parent composite account, if any."""
        if self._parent is not None and isinstance(self._parent, CompositeTAccount):
            self._parent._recalculate()  # noqa: SLF001


class CompositeTAccount(TAccount):
    """Composite T-account that can hold multiple sub T-accounts.

    A composite account aggregates the balances of its children. Debiting or
    crediting a child automatically recalculates the parent's totals.

    Example -- Investment Securities (composite)::

        Investment Securities  [composite, debit-normal]
          +-- Investment HTM       debit: 5,000
          +-- Investment FVOCI     debit: 3,000
          = total debit: 8,000
    """

    def __init__(  # noqa: PLR0913
        self,
        name: str,
        account_type: AccountType,
        contra_accounts: list[TAccount] | None = None,
        parent: TAccount | None = None,
        debit: float = 0.0,
        credit: float = 0.0,
        *,
        is_contra_account: bool = False,
    ) -> None:
        """Initialize a CompositeTAccount instance."""
        super().__init__(
            name,
            account_type,
            contra_accounts,
            parent,
            debit,
            credit,
            is_contra_account=is_contra_account,
        )
        self._sub_accounts: list[TAccount] = []

    @property
    def sub_accounts(self) -> Generator[TAccount, None, None]:
        """Return an iterator over sub-accounts."""
        yield from self._sub_accounts

    def is_composite(self) -> bool:
        """Check if the T-account is composite."""
        return True

    def has_sub_account(self) -> bool:
        """Check if the T-account has any sub account."""
        return len(self._sub_accounts) > 0

    def leaves(self) -> Generator[TAccount, None, None]:
        """Recursively yield all leaf accounts in this composite's sub-tree."""
        if not self.has_sub_account():
            yield self
            return
        for child in self._sub_accounts:
            yield from child.leaves()

    def add(self, account: TAccount) -> None:
        """Add a T-account as a child."""
        if not isinstance(account, TAccount):
            error_message = "Account must be an instance of TAccount"
            raise TypeError(error_message)
        self._sub_accounts.append(account)
        account.parent = self
        self._recalculate()

    def remove(self, account: TAccount) -> None:
        """Remove a T-account as a child."""
        self._sub_accounts.remove(account)
        account.parent = None
        self._recalculate()

    def _recalculate(self) -> None:
        """Recalculate debit and credit values from sub-accounts and propagate upward."""
        self._debit_value = sum(account.debit_value for account in self._sub_accounts)
        self._credit_value = sum(account.credit_value for account in self._sub_accounts)
        self._propagate_to_parent()
