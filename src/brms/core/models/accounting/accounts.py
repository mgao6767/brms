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
        self._guard_composite_direct_posting()
        self._debit_value = value
        self._propagate_to_parent()

    @property
    def credit_value(self) -> float:
        """Return the credit value of the account."""
        return self._credit_value

    @credit_value.setter
    def credit_value(self, value: float) -> None:
        self._guard_composite_direct_posting()
        self._credit_value = value
        self._propagate_to_parent()

    @property
    def sub_accounts(self) -> Generator[TAccount, None, None]:
        """Yield direct child accounts. Empty for simple accounts."""
        yield from ()

    def has_contra_account(self) -> bool:
        """Check if this account has any contra accounts attached."""
        return len(self.contra_accounts) > 0

    def posting_accounts(self) -> Generator[TAccount, None, None]:
        """Yield all accounts that can directly receive debit/credit postings.

        For a simple account, yields itself.
        For a composite account, recursively yields the lowest-level accounts
        in the hierarchy that are not themselves composites with children.

        The ledger uses this when building closing entries to ensure postings
        go to accounts that accept direct value changes.
        """
        yield self

    def balance(self) -> float:
        """Return the net balance of this account.

        Debit-normal accounts: balance = debits - credits.
        Credit-normal accounts: balance = credits - debits.
        """
        if self.normal_balance == AccountNormalBalance.DEBIT_NORMAL:
            return self.debit_value - self.credit_value
        return self.credit_value - self.debit_value

    def _guard_composite_direct_posting(self) -> None:
        """Raise if this is a composite account with children.

        Composite accounts derive their values from children. Direct debit/credit
        on a composite would be overwritten by the next recalculation, so we
        prevent it. Only posting accounts should be posted to directly.

        Base TAccount is never composite, so this is a no-op.
        CompositeTAccount overrides this to check for children.
        """

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
        """Yield direct child accounts."""
        yield from self._sub_accounts

    def posting_accounts(self) -> Generator[TAccount, None, None]:
        """Recursively yield the lowest-level accounts that accept direct postings.

        If this composite has no children, yields itself.
        Otherwise, recurses into each child's posting_accounts.
        """
        if not self._sub_accounts:
            yield self
            return
        for child in self._sub_accounts:
            yield from child.posting_accounts()

    def add_sub_account(self, account: TAccount) -> None:
        """Add a child account to this composite.

        The child's parent is set to this account, and balances are recalculated.
        """
        self._sub_accounts.append(account)
        account.parent = self
        self._recalculate()

    def remove_sub_account(self, account: TAccount) -> None:
        """Remove a child account from this composite."""
        self._sub_accounts.remove(account)
        account.parent = None
        self._recalculate()

    def _guard_composite_direct_posting(self) -> None:
        """Raise if this composite has children (values must come from children)."""
        if self._sub_accounts:
            msg = "Cannot post directly to a composite account with sub-accounts"
            raise ValueError(msg)

    def _recalculate(self) -> None:
        """Recalculate debit and credit values from sub-accounts and propagate upward."""
        self._debit_value = sum(account.debit_value for account in self._sub_accounts)
        self._credit_value = sum(account.credit_value for account in self._sub_accounts)
        self._propagate_to_parent()
