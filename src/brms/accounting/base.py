from enum import Enum

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
    def get_normal_balance(account_type: "AccountType") -> AccountNormalBalance:
        """Return the normal balance for a given account type."""
        match account_type:
            case AccountType.ASSET | AccountType.EXPENSE:
                return AccountNormalBalance.DEBIT_NORMAL
            case AccountType.LIABILITY | AccountType.EQUITY | AccountType.INCOME:
                return AccountNormalBalance.CREDIT_NORMAL
            case _:
                error_message = f"Unknown account type: {account_type}"
                raise ValueError(error_message)


class Account(Observable):
    """Represent a single account in the chart of accounts.

    Leaf node that holds a value and notifies observers on change.
    """

    def __init__(
        self,
        name: str,
        account_type: AccountType,
        contra_accounts: list["Account"] | None = None,
        value: float = 0.0,
    ) -> None:
        """Initialize an Account instance."""
        super().__init__()
        self.name = name
        self.type = account_type
        self.normal_balance = AccountType.get_normal_balance(account_type)
        self.contra_accounts = contra_accounts or []
        self._value = value

    @property
    def value(self) -> float:
        """Return the (aggregated) value of the account."""
        return self._value

    @value.setter
    def value(self, value: float) -> None:
        if self.is_composite():
            error_message = "Cannot set value directly on a composite account"
            raise ValueError(error_message)
        self._value = value
        self.notify_observers()  # Notify parent (if any) of the value change

    def is_composite(self) -> bool:
        """Check if the account is composite."""
        return False


class CompositeAccount(Account, Observable, Observer):
    """Represent a single account that may have sub-accounts in the chart of accounts.

    Composite node that observes children and aggregates their values.
    """

    def __init__(
        self,
        name: str,
        account_type: AccountType,
        contra_accounts: list["Account"] | None = None,
        value: float = 0.0,
    ) -> None:
        """Initialize a CompositeAccount instance."""
        super().__init__(name, account_type, contra_accounts, value)
        self.accounts: list[Account] = []

    def is_composite(self) -> bool:
        """Check if the account is composite."""
        return True

    def add(self, account: Account) -> None:
        """Add an account as a child and observe it."""
        if account.type != self.type:
            error_message = f"Account type mismatch: {account.type} != {self.type}"
            raise ValueError(error_message)
        self.accounts.append(account)
        account.add_observer(self)  # Observe the child
        self.update(account)  # Update value to include the new child

    def remove(self, account: Account) -> None:
        """Remove an account as a child and stop observing it."""
        self.accounts.remove(account)
        account.remove_observer(self)  # Stop observing the child
        self.update(account)  # Update value to exclude the removed child

    def update(self, observable: Observable) -> None:
        """Triggered when a child account notifies of a change."""
        if not isinstance(observable, Account):
            error_message = "Observable must be an instance of Account"
            raise TypeError(error_message)
        self._value = sum(account.value for account in self.accounts)
        self.notify_observers()  # Notify parent (if any) of the change


class ChartOfAccounts:
    """Represent the chart of accounts."""


class TAccount(Observable):
    """Base class representing a T-account, which holds amounts on both the debit and credit sides.

    Simple T-account with no sub-accounts.
    """

    def __init__(self, account_type: AccountType, debit: float = 0.0, credit: float = 0.0) -> None:
        """Initialize a TAccount instance."""
        super().__init__()
        self.type = account_type
        self.normal_balance = AccountType.get_normal_balance(account_type)
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
    def debit_value(self) -> float:
        """Return the debit value of the account."""
        return self._debit_value

    @debit_value.setter
    def debit_value(self, value: float) -> None:
        if self.is_composite():
            error_message = "Cannot set value directly on a composite account"
            raise ValueError(error_message)
        self._debit_value = value
        self.notify_observers()  # Notify parent (if any) of the value change

    @property
    def credit_value(self) -> float:
        """Return the credit value of the account."""
        return self._credit_value

    @credit_value.setter
    def credit_value(self, value: float) -> None:
        if self.is_composite():
            error_message = "Cannot set value directly on a composite account"
            raise ValueError(error_message)
        self._credit_value = value
        self.notify_observers()  # Notify parent (if any) of the value change

    def is_composite(self) -> bool:
        """Check if the T-account is composite."""
        return False

    def balance(self) -> float:
        """Return account balance."""
        match self.normal_balance:
            case AccountNormalBalance.DEBIT_NORMAL:
                return self.debit_value - self.credit_value
            case AccountNormalBalance.CREDIT_NORMAL:
                return self.credit_value - self.debit_value


class CompositeTAccount(TAccount, Observable, Observer):
    """Composite T-account that can hold multiple sub T-accounts."""

    def __init__(self, account_type: AccountType, debit: float = 0.0, credit: float = 0.0) -> None:
        """Initialize a CompositeTAccount instance."""
        super().__init__(account_type, debit, credit)
        self.sub_accounts: list[TAccount] = []

    def is_composite(self) -> bool:
        """Check if the T-account is composite."""
        return True

    def add(self, account: TAccount) -> None:
        """Add a T-account as a child and observe it."""
        if account.type != self.type:
            error_message = f"Account type mismatch: {account.type} != {self.type}"
            raise ValueError(error_message)
        if not isinstance(account, TAccount):
            error_message = "Account must be an instance of TAccount"
            raise TypeError(error_message)
        self.sub_accounts.append(account)
        account.add_observer(self)  # Observe the child
        self.update(account)  # Update value to include the new child

    def remove(self, account: TAccount) -> None:
        """Remove a T-account as a child and stop observing it."""
        self.sub_accounts.remove(account)
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
