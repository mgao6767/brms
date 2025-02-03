"""Module for various types of accounts used in a bank's chart of accounts."""

from collections import UserDict
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


class AccountBalances(UserDict["TAccount", float]):
    """A dictionary-like class to hold account balances."""

    @classmethod
    def from_accounts(cls, accounts: list["TAccount"]) -> "AccountBalances":
        """Create an AccountBalances instance from a list of accounts."""
        balances = cls()
        for account in accounts:
            balances[account] = account.balance()
        return balances


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
        description: str = "",
        *,
        is_contra_account: bool = False,
        is_temporary_account: bool = False,
    ) -> None:
        """Initialize a TAccount instance."""
        super().__init__()
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
    def parent(self) -> Optional["TAccount"]:
        """Get the parent account."""
        return self._parent

    @parent.setter
    def parent(self, parent: Optional["TAccount"]) -> None:
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

    @property
    def sub_accounts(self) -> Generator["TAccount", None, None]:
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
    def sub_accounts(self) -> Generator["TAccount", None, None]:
        """Return an iterator over sub-accounts."""
        yield from self._sub_accounts

    def is_composite(self) -> bool:
        """Check if the T-account is composite."""
        return True

    def has_sub_account(self) -> bool:
        """Check if the T-account has any sub account."""
        return len(self._sub_accounts) > 0

    def add(self, account: TAccount) -> None:
        """Add a T-account as a child and observe it."""
        # Do not require same type because Trading Income contains Gains (income) and Losses (expense)
        if not isinstance(account, TAccount):
            error_message = "Account must be an instance of TAccount"
            raise TypeError(error_message)
        self._sub_accounts.append(account)
        account.parent = self
        account.add_observer(self)  # Observe the child
        self.update(account)  # Update value to include the new child

    def remove(self, account: TAccount) -> None:
        """Remove a T-account as a child and stop observing it."""
        self._sub_accounts.remove(account)
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


class CashAccount(TAccount):
    """Cash account."""

    def __init__(self) -> None:
        super().__init__("Cash and Cash Equivalents", AccountType.ASSET)


class ReceivableAccount(TAccount):
    """Receivable account."""

    def __init__(self) -> None:
        super().__init__("Receivables from Financial Institutions", AccountType.ASSET)


class LoanAccount(TAccount):
    """Loan account.

    Loans provided to customers that the bank intends to hold until maturity and collect principal and interest.
    - Banking Book only
    """

    def __init__(self) -> None:
        super().__init__("Loans and Advances", AccountType.ASSET)


class AssetFVTPLAccount(TAccount):
    """Asset FVTPL account, or Financial Assets - Trading (FVTPL).

    Assets at Fair Value Through Income Statement (FVTPL)
    - Trading Book securities
    """

    def __init__(self) -> None:
        super().__init__("Assets at FVTPL", AccountType.ASSET)


class InvestmentSecuritiesAccount(CompositeTAccount):
    """Investment securities account."""

    def __init__(self) -> None:
        super().__init__("Investment Securities", AccountType.ASSET)
        self.investment_htm_account = InvestmentHTMAccount()
        self.investment_fvoci_account = InvestmentFVOCIAccount()
        self.add(self.investment_htm_account)
        self.add(self.investment_fvoci_account)


class InvestmentHTMAccount(TAccount):
    """Investment HTM account, or Investment Securities at Amortized Cost.

    Investment Securities at Amortized Cost (HTM - Held to Maturity)
    This account includes debt securities (bonds, treasuries) that the bank intends to hold until maturity.
    - Banking Book only
    - No fair value adjustments unless impaired.
    """

    def __init__(self) -> None:
        super().__init__("Investment Securities at Amortized Cost", AccountType.ASSET)


class InvestmentFVOCIAccount(TAccount):
    """Investment FVOCI account.

    Investment Securities at Fair Value Through Other Comprehensive Income (FVOCI)
    - Banking Book: Some debt securities where the bank intends to collect cash flows and sell occasionally.
    - Changes in fair value are recorded in OCI, not P&L, until sale.
    """

    def __init__(self) -> None:
        super().__init__(
            "Investment Securities at FVOCI",
            AccountType.ASSET,
        )


class PPEAccount(TAccount):
    """PPE account."""

    def __init__(self) -> None:
        super().__init__("Property, Plant and Equipment", AccountType.ASSET)


class IntangibleAccount(TAccount):
    """Intangible account."""

    def __init__(self) -> None:
        super().__init__("Intangible Assets", AccountType.ASSET)


class DepositAccount(CompositeTAccount):
    """Deposit account."""

    def __init__(self) -> None:
        super().__init__("Deposits and Other Public Borrowings", AccountType.LIABILITY)
        self.customer_deposits_account = CustomerDepositAccount()
        self.public_borrowing_account = PublicBorrowingsAccount()
        self.add(self.customer_deposits_account)
        self.add(self.public_borrowing_account)


class CustomerDepositAccount(TAccount):
    """Customer deposit account."""

    def __init__(self) -> None:
        super().__init__("Deposits", AccountType.LIABILITY)


class PublicBorrowingsAccount(TAccount):
    """Public borrowings account.

    Other public borrowings (typically short-term)
    """

    def __init__(self) -> None:
        super().__init__("Other Public Borrowings", AccountType.LIABILITY)


class PayableAccount(TAccount):
    """Payable account."""

    def __init__(self) -> None:
        super().__init__("Payables to Financial Institutions", AccountType.LIABILITY)


class DebtAccount(TAccount):
    """Debt account.

    Debt issues (typically long-term)
    """

    def __init__(self) -> None:
        super().__init__("Debt Issues", AccountType.LIABILITY)


class EquityAccount(TAccount):
    """Equity account."""

    def __init__(self) -> None:
        super().__init__("Shareholders' Equity", AccountType.EQUITY)


class InterestIncomeAccount(CompositeTAccount):
    """Interest income account."""

    def __init__(self) -> None:
        super().__init__("Interest Income", AccountType.INCOME)


class RealizedTradingGainAccount(TAccount):
    """Realized Trading Gain account."""

    def __init__(self) -> None:
        super().__init__("Realized Trading Gain", AccountType.INCOME)


class UnrealizedTradingGainAccount(TAccount):
    """Unrealized Trading Gain account."""

    def __init__(self) -> None:
        super().__init__("Unrealized Trading Gain", AccountType.INCOME)


class RealizedTradingLossAccount(TAccount):
    """Realized Trading Loss account."""

    def __init__(self) -> None:
        super().__init__("Realized Trading Loss", AccountType.EXPENSE)


class UnrealizedTradingLossAccount(TAccount):
    """Unrealized Trading Loss account."""

    def __init__(self) -> None:
        super().__init__("Unrealized Trading Loss", AccountType.EXPENSE)


class RealizedTradingPnLAccount(TAccount):
    """Realized Trading P&L account."""

    def __init__(self) -> None:
        super().__init__("Realized Trading P&L", AccountType.INCOME)


class UnrealizedTradingPnLAccount(TAccount):
    """Unrealized Trading P&L account."""

    def __init__(self) -> None:
        super().__init__("Unrealized Trading P&L", AccountType.INCOME)


class TradingIncomeAccount(CompositeTAccount):
    """Trading income account."""

    def __init__(self) -> None:
        super().__init__("Trading Income (FVTPL)", AccountType.INCOME)
        self.unrealized_trading_gain_account = UnrealizedTradingGainAccount()
        self.realized_trading_gain_account = RealizedTradingGainAccount()
        self.unrealized_trading_loss_account = UnrealizedTradingLossAccount()
        self.realized_trading_loss_account = RealizedTradingLossAccount()
        self.add(self.unrealized_trading_gain_account)
        self.add(self.realized_trading_gain_account)
        self.add(self.unrealized_trading_loss_account)
        self.add(self.realized_trading_loss_account)


class UnrealizedOCIGainAccount(TAccount):
    """Unrealized OCI Gain account."""

    def __init__(self, contra_accounts: list[TAccount]) -> None:
        super().__init__("Unrealized OCI Gain", AccountType.EQUITY, contra_accounts)


class UnrealizedOCILossAccount(TAccount):
    """Unrealized OCI Loss account."""

    def __init__(self) -> None:
        super().__init__("Unrealized OCI Loss", AccountType.EQUITY, is_contra_account=True)


class AccumulatedOCIAccount(CompositeTAccount):
    """Accumulated OCI account."""

    def __init__(self) -> None:
        super().__init__("Accumulated OCI", AccountType.EQUITY)
        self.unrealized_oci_loss_account = UnrealizedOCILossAccount()
        self.unrealized_oci_gain_account = UnrealizedOCIGainAccount(contra_accounts=[self.unrealized_oci_loss_account])
        self.add(self.unrealized_oci_gain_account)
        self.add(self.unrealized_oci_loss_account)


class RealizedOCIGainAccount(TAccount):
    """Realized OCI Gain account."""

    def __init__(self) -> None:
        super().__init__("Realized OCI Gain", AccountType.INCOME)


class RealizedOCILossAccount(TAccount):
    """Realized OCI Loss account."""

    def __init__(self) -> None:
        super().__init__("Realized OCI Loss", AccountType.EXPENSE)


class InvestmentIncomeAccount(CompositeTAccount):
    """Investment income account."""

    def __init__(self) -> None:
        super().__init__("Investment Income (FVOCI)", AccountType.INCOME)
        self.realized_oci_gain_account = RealizedOCIGainAccount()
        self.realized_oci_loss_account = RealizedOCILossAccount()
        self.add(self.realized_oci_gain_account)
        self.add(self.realized_oci_loss_account)


class InterestExpenseAccount(TAccount):
    """Interest expense account."""

    def __init__(self) -> None:
        super().__init__("Interest Expense", AccountType.EXPENSE)


class OperatingExpenseAccount(TAccount):
    """Operating expense account."""

    def __init__(self) -> None:
        super().__init__("Operating Expense", AccountType.EXPENSE)


class RetainedEarningsAccount(TAccount):
    """Represent the retained earnings account."""

    def __init__(self) -> None:
        super().__init__("Retained Earnings", AccountType.EQUITY)


class IncomeSummaryAccount(TAccount):
    """Represent the income summary account."""

    def __init__(self) -> None:
        super().__init__("Income Summary Account", AccountType.INCOME, is_temporary_account=True)


@dataclass
class ChartOfAccounts:
    """Represent the chart of accounts."""

    assets: list[TAccount] = field(default_factory=list)
    equities: list[TAccount] = field(default_factory=list)
    liabilities: list[TAccount] = field(default_factory=list)
    income: list[TAccount] = field(default_factory=list)
    expenses: list[TAccount] = field(default_factory=list)

    income_summary_account: IncomeSummaryAccount = field(default_factory=IncomeSummaryAccount)
    retained_earnings_account: RetainedEarningsAccount = field(default_factory=RetainedEarningsAccount)

    def __iter__(self) -> Generator[TAccount, None, None]:
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


@dataclass
class BankChartOfAccounts(ChartOfAccounts):
    """Represent the chart of accounts."""

    # Asset accounts
    cash_account: CashAccount = field(default_factory=CashAccount)
    receivable_account: ReceivableAccount = field(default_factory=ReceivableAccount)
    loan_account: LoanAccount = field(default_factory=LoanAccount)
    asset_fvtpl_account: AssetFVTPLAccount = field(default_factory=AssetFVTPLAccount)
    investment_securities_account: InvestmentSecuritiesAccount = field(default_factory=InvestmentSecuritiesAccount)
    ppe_account: PPEAccount = field(default_factory=PPEAccount)
    intangible_account: IntangibleAccount = field(default_factory=IntangibleAccount)
    # Liabilit accounts
    deposit_account: DepositAccount = field(default_factory=DepositAccount)
    payable_account: PayableAccount = field(default_factory=PayableAccount)
    debt_account: DebtAccount = field(default_factory=DebtAccount)
    # Equity accounts
    equity_account: EquityAccount = field(default_factory=EquityAccount)
    accumulated_oci_account: AccumulatedOCIAccount = field(default_factory=AccumulatedOCIAccount)
    # Income statement accounts
    interest_income_account: InterestIncomeAccount = field(default_factory=InterestIncomeAccount)
    trading_income_account: TradingIncomeAccount = field(default_factory=TradingIncomeAccount)
    investment_income_account: InvestmentIncomeAccount = field(default_factory=InvestmentIncomeAccount)
    interest_expense_account: InterestExpenseAccount = field(default_factory=InterestExpenseAccount)
    operating_expense_account: OperatingExpenseAccount = field(default_factory=OperatingExpenseAccount)

    def __post_init__(self) -> None:
        # Direct acess to sub accounts of composite account
        self.investment_htm_account = self.investment_securities_account.investment_htm_account
        self.investment_fvoci_account = self.investment_securities_account.investment_fvoci_account

        self.customer_deposits_account = self.deposit_account.customer_deposits_account
        self.public_borrowings_account = self.deposit_account.public_borrowing_account

        self.unrealized_oci_gain_account = self.accumulated_oci_account.unrealized_oci_gain_account
        self.unrealized_oci_loss_account = self.accumulated_oci_account.unrealized_oci_loss_account

        self.unrealized_trading_gain_account = self.trading_income_account.unrealized_trading_gain_account
        self.realized_trading_gain_account = self.trading_income_account.realized_trading_gain_account
        self.unrealized_trading_loss_account = self.trading_income_account.unrealized_trading_loss_account
        self.realized_trading_loss_account = self.trading_income_account.realized_trading_loss_account

        self.realized_oci_gain_account = self.investment_income_account.realized_oci_gain_account
        self.realized_oci_loss_account = self.investment_income_account.realized_oci_loss_account

        self.assets.append(self.cash_account)
        self.assets.append(self.receivable_account)
        self.assets.append(self.loan_account)
        self.assets.append(self.asset_fvtpl_account)  # trading book instruments
        self.assets.append(self.investment_securities_account)  # includes HTM and FVOCI subaccounts
        self.assets.append(self.ppe_account)
        self.assets.append(self.intangible_account)
        self.liabilities.append(self.deposit_account)  # includes two subaccounts
        self.liabilities.append(self.payable_account)
        self.liabilities.append(self.debt_account)
        self.equities.append(self.equity_account)
        self.equities.append(self.accumulated_oci_account)
        self.income.append(self.interest_income_account)
        self.income.append(self.trading_income_account)
        self.income.append(self.investment_income_account)
        self.expenses.append(self.interest_expense_account)
        self.expenses.append(self.operating_expense_account)
