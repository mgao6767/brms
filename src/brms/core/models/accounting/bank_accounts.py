"""Bank-specific account classes and chart of accounts for a commercial bank.

This module defines concrete T-account subclasses used in commercial banking
and a pre-configured :class:`BankChartOfAccounts` that wires them together.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from brms.core.models.accounting.accounts import AccountType, CompositeTAccount, TAccount
from brms.core.models.accounting.chart_of_accounts import ChartOfAccounts

# ---------------------------------------------------------------------------
# Asset accounts
# ---------------------------------------------------------------------------


class CashAccount(TAccount):
    """Cash account."""

    def __init__(self) -> None:
        """Initialize a CashAccount instance."""
        super().__init__("Cash and Cash Equivalents", AccountType.ASSET)


class ReceivableAccount(TAccount):
    """Receivable account."""

    def __init__(self) -> None:
        """Initialize a ReceivableAccount instance."""
        super().__init__("Receivables from Financial Institutions", AccountType.ASSET)


class LoanAccount(TAccount):
    """Loan account.

    Loans provided to customers that the bank intends to hold until maturity and collect principal and interest.
    - Banking Book only
    """

    def __init__(self) -> None:
        """Initialize a LoanAccount instance."""
        super().__init__("Loans and Advances", AccountType.ASSET)


class AssetFVTPLAccount(TAccount):
    """Asset FVTPL account, or Financial Assets - Trading (FVTPL).

    Assets at Fair Value Through Income Statement (FVTPL)
    - Trading Book securities
    """

    def __init__(self) -> None:
        """Initialize an AssetFVTPLAccount instance."""
        super().__init__("Assets at FVTPL", AccountType.ASSET)


class InvestmentHTMAccount(TAccount):
    """Investment HTM account, or Investment Securities at Amortized Cost.

    Investment Securities at Amortized Cost (HTM - Held to Maturity)
    This account includes debt securities (bonds, treasuries) that the bank intends to hold until maturity.
    - Banking Book only
    - No fair value adjustments unless impaired.
    """

    def __init__(self) -> None:
        """Initialize an InvestmentHTMAccount instance."""
        super().__init__("Investment Securities at Amortized Cost", AccountType.ASSET)


class InvestmentFVOCIAccount(TAccount):
    """Investment FVOCI account.

    Investment Securities at Fair Value Through Other Comprehensive Income (FVOCI)
    - Banking Book: Some debt securities where the bank intends to collect cash flows and sell occasionally.
    - Changes in fair value are recorded in OCI, not P&L, until sale.
    """

    def __init__(self) -> None:
        """Initialize an InvestmentFVOCIAccount instance."""
        super().__init__(
            "Investment Securities at FVOCI",
            AccountType.ASSET,
        )


class InvestmentSecuritiesAccount(CompositeTAccount):
    """Investment securities account."""

    def __init__(self) -> None:
        """Initialize an InvestmentSecuritiesAccount instance."""
        super().__init__("Investment Securities", AccountType.ASSET)
        self.investment_htm_account = InvestmentHTMAccount()
        self.investment_fvoci_account = InvestmentFVOCIAccount()
        self.add(self.investment_htm_account)
        self.add(self.investment_fvoci_account)


class PPEAccount(TAccount):
    """PPE account."""

    def __init__(self) -> None:
        """Initialize a PPEAccount instance."""
        super().__init__("Property, Plant and Equipment", AccountType.ASSET)


class IntangibleAccount(TAccount):
    """Intangible account."""

    def __init__(self) -> None:
        """Initialize an IntangibleAccount instance."""
        super().__init__("Intangible Assets", AccountType.ASSET)


# ---------------------------------------------------------------------------
# Liability accounts
# ---------------------------------------------------------------------------


class CustomerDepositAccount(TAccount):
    """Customer deposit account."""

    def __init__(self) -> None:
        """Initialize a CustomerDepositAccount instance."""
        super().__init__("Deposits", AccountType.LIABILITY)


class PublicBorrowingsAccount(TAccount):
    """Public borrowings account.

    Other public borrowings (typically short-term)
    """

    def __init__(self) -> None:
        """Initialize a PublicBorrowingsAccount instance."""
        super().__init__("Other Public Borrowings", AccountType.LIABILITY)


class DepositAccount(CompositeTAccount):
    """Deposit account."""

    def __init__(self) -> None:
        """Initialize a DepositAccount instance."""
        super().__init__("Deposits and Other Public Borrowings", AccountType.LIABILITY)
        self.customer_deposits_account = CustomerDepositAccount()
        self.public_borrowing_account = PublicBorrowingsAccount()
        self.add(self.customer_deposits_account)
        self.add(self.public_borrowing_account)


class PayableAccount(TAccount):
    """Payable account."""

    def __init__(self) -> None:
        """Initialize a PayableAccount instance."""
        super().__init__("Payables to Financial Institutions", AccountType.LIABILITY)


class DebtAccount(TAccount):
    """Debt account.

    Debt issues (typically long-term)
    """

    def __init__(self) -> None:
        """Initialize a DebtAccount instance."""
        super().__init__("Debt Issues", AccountType.LIABILITY)


# ---------------------------------------------------------------------------
# Equity accounts
# ---------------------------------------------------------------------------


class EquityAccount(TAccount):
    """Equity account."""

    def __init__(self) -> None:
        """Initialize an EquityAccount instance."""
        super().__init__("Shareholders' Equity", AccountType.EQUITY)


class UnrealizedOCILossAccount(TAccount):
    """Unrealized OCI Loss account."""

    def __init__(self) -> None:
        """Initialize an UnrealizedOCILossAccount instance."""
        super().__init__("Unrealized OCI Loss", AccountType.EQUITY, is_contra_account=True)


class UnrealizedOCIGainAccount(TAccount):
    """Unrealized OCI Gain account."""

    def __init__(self, contra_accounts: list[TAccount]) -> None:
        """Initialize an UnrealizedOCIGainAccount instance."""
        super().__init__("Unrealized OCI Gain", AccountType.EQUITY, contra_accounts)


class AccumulatedOCIAccount(CompositeTAccount):
    """Accumulated OCI account."""

    def __init__(self) -> None:
        """Initialize an AccumulatedOCIAccount instance."""
        super().__init__("Accumulated OCI", AccountType.EQUITY)
        self.unrealized_oci_loss_account = UnrealizedOCILossAccount()
        self.unrealized_oci_gain_account = UnrealizedOCIGainAccount(contra_accounts=[self.unrealized_oci_loss_account])
        self.add(self.unrealized_oci_gain_account)
        self.add(self.unrealized_oci_loss_account)


# ---------------------------------------------------------------------------
# Income accounts
# ---------------------------------------------------------------------------


class InterestIncomeAccount(CompositeTAccount):
    """Interest income account."""

    def __init__(self) -> None:
        """Initialize an InterestIncomeAccount instance."""
        super().__init__("Interest Income", AccountType.INCOME)


class RealizedTradingGainAccount(TAccount):
    """Realized Trading Gain account."""

    def __init__(self) -> None:
        """Initialize a RealizedTradingGainAccount instance."""
        super().__init__("Realized Trading Gain", AccountType.INCOME)


class UnrealizedTradingGainAccount(TAccount):
    """Unrealized Trading Gain account."""

    def __init__(self) -> None:
        """Initialize an UnrealizedTradingGainAccount instance."""
        super().__init__("Unrealized Trading Gain", AccountType.INCOME)


class RealizedTradingLossAccount(TAccount):
    """Realized Trading Loss account."""

    def __init__(self) -> None:
        """Initialize a RealizedTradingLossAccount instance."""
        super().__init__("Realized Trading Loss", AccountType.EXPENSE)


class UnrealizedTradingLossAccount(TAccount):
    """Unrealized Trading Loss account."""

    def __init__(self) -> None:
        """Initialize an UnrealizedTradingLossAccount instance."""
        super().__init__("Unrealized Trading Loss", AccountType.EXPENSE)


class RealizedTradingPnLAccount(TAccount):
    """Realized Trading P&L account."""

    def __init__(self) -> None:
        """Initialize a RealizedTradingPnLAccount instance."""
        super().__init__("Realized Trading P&L", AccountType.INCOME)


class UnrealizedTradingPnLAccount(TAccount):
    """Unrealized Trading P&L account."""

    def __init__(self) -> None:
        """Initialize an UnrealizedTradingPnLAccount instance."""
        super().__init__("Unrealized Trading P&L", AccountType.INCOME)


class TradingIncomeAccount(CompositeTAccount):
    """Trading income account."""

    def __init__(self) -> None:
        """Initialize a TradingIncomeAccount instance."""
        super().__init__("Trading Income (FVTPL)", AccountType.INCOME)
        self.unrealized_trading_gain_account = UnrealizedTradingGainAccount()
        self.realized_trading_gain_account = RealizedTradingGainAccount()
        self.unrealized_trading_loss_account = UnrealizedTradingLossAccount()
        self.realized_trading_loss_account = RealizedTradingLossAccount()
        self.add(self.unrealized_trading_gain_account)
        self.add(self.realized_trading_gain_account)
        self.add(self.unrealized_trading_loss_account)
        self.add(self.realized_trading_loss_account)


class RealizedOCIGainAccount(TAccount):
    """Realized OCI Gain account."""

    def __init__(self) -> None:
        """Initialize a RealizedOCIGainAccount instance."""
        super().__init__("Realized OCI Gain", AccountType.INCOME)


class RealizedOCILossAccount(TAccount):
    """Realized OCI Loss account."""

    def __init__(self) -> None:
        """Initialize a RealizedOCILossAccount instance."""
        super().__init__("Realized OCI Loss", AccountType.EXPENSE)


class InvestmentIncomeAccount(CompositeTAccount):
    """Investment income account."""

    def __init__(self) -> None:
        """Initialize an InvestmentIncomeAccount instance."""
        super().__init__("Investment Income (FVOCI)", AccountType.INCOME)
        self.realized_oci_gain_account = RealizedOCIGainAccount()
        self.realized_oci_loss_account = RealizedOCILossAccount()
        self.add(self.realized_oci_gain_account)
        self.add(self.realized_oci_loss_account)


# ---------------------------------------------------------------------------
# Expense accounts
# ---------------------------------------------------------------------------


class InterestExpenseAccount(TAccount):
    """Interest expense account."""

    def __init__(self) -> None:
        """Initialize an InterestExpenseAccount instance."""
        super().__init__("Interest Expense", AccountType.EXPENSE)


class OperatingExpenseAccount(TAccount):
    """Operating expense account."""

    def __init__(self) -> None:
        """Initialize an OperatingExpenseAccount instance."""
        super().__init__("Operating Expense", AccountType.EXPENSE)


# ---------------------------------------------------------------------------
# Bank Chart of Accounts
# ---------------------------------------------------------------------------


@dataclass
class BankChartOfAccounts(ChartOfAccounts):
    """Pre-configured chart of accounts for a commercial bank.

    Account hierarchy::

        +-- Assets
        |   +-- Cash and Cash Equivalents
        |   +-- Receivables from Financial Institutions
        |   +-- Loans and Advances
        |   +-- Assets at FVTPL (Trading Book)
        |   +-- Investment Securities (Composite)
        |   |   +-- Investment Securities at Amortized Cost (HTM)
        |   |   +-- Investment Securities at FVOCI
        |   +-- Property, Plant and Equipment
        |   +-- Intangible Assets
        +-- Liabilities
        |   +-- Deposits and Other Public Borrowings (Composite)
        |   |   +-- Deposits (Customer)
        |   |   +-- Other Public Borrowings
        |   +-- Payables to Financial Institutions
        |   +-- Debt Issues
        +-- Equity
        |   +-- Shareholders' Equity
        |   +-- Accumulated OCI (Composite)
        |       +-- Unrealized OCI Gain
        |       +-- Unrealized OCI Loss
        +-- Income
        |   +-- Interest Income
        |   +-- Trading Income - FVTPL (Composite)
        |   |   +-- Unrealized Trading Gain
        |   |   +-- Realized Trading Gain
        |   |   +-- Unrealized Trading Loss
        |   |   +-- Realized Trading Loss
        |   +-- Investment Income - FVOCI (Composite)
        |       +-- Realized OCI Gain
        |       +-- Realized OCI Loss
        +-- Expenses
            +-- Interest Expense
            +-- Operating Expense
    """

    # Asset accounts
    cash_account: CashAccount = field(default_factory=CashAccount)
    receivable_account: ReceivableAccount = field(default_factory=ReceivableAccount)
    loan_account: LoanAccount = field(default_factory=LoanAccount)
    asset_fvtpl_account: AssetFVTPLAccount = field(default_factory=AssetFVTPLAccount)
    investment_securities_account: InvestmentSecuritiesAccount = field(default_factory=InvestmentSecuritiesAccount)
    ppe_account: PPEAccount = field(default_factory=PPEAccount)
    intangible_account: IntangibleAccount = field(default_factory=IntangibleAccount)
    # Liability accounts
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
        """Set up direct access to sub-accounts and populate account lists."""
        # Direct access to sub accounts of composite account
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
