from abc import ABC, abstractmethod
from enum import Enum


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


class Observable:
    """Base class for observable components."""

    def __init__(self) -> None:
        """Initialize the Observable with an empty list of observers."""
        self._observers: list[Observer] = []

    def add_observer(self, observer: "Observer") -> None:
        """Add an observer to the list of observers."""
        self._observers.append(observer)

    def remove_observer(self, observer: "Observer") -> None:
        """Remove an observer from the list of observers."""
        self._observers.remove(observer)

    def notify_observers(self) -> None:
        """Notify all observers about a change."""
        for observer in self._observers:
            observer.update(self)


class Observer(ABC):
    """Base class for observers."""

    @abstractmethod
    def update(self, observable: Observable) -> None:
        """Update when a observable notifies of a change."""


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
        self._value = value
        self.notify_observers()  # Notify parent (if any) of the value change


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
