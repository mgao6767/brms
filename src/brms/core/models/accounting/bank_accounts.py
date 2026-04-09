"""Pre-configured chart of accounts for a commercial bank.

All bank-specific accounts are created as plain ``TAccount`` or
``CompositeTAccount`` instances — no subclasses needed.  The
:class:`BankChartOfAccounts` uses :class:`ChartOfAccountsBuilder`
to construct and validate the chart.
"""

from __future__ import annotations

from brms.core.models.accounting.accounts import AccountType, CompositeTAccount, TAccount
from brms.core.models.accounting.chart_of_accounts import ChartOfAccounts, ChartOfAccountsBuilder


class BankChartOfAccounts(ChartOfAccounts):
    """Pre-configured chart of accounts for a commercial bank.

    Every account is accessible as a named attribute.  Composite accounts
    automatically aggregate their sub-accounts.  Contra accounts reduce the
    balance of the account they are attached to.

    Account hierarchy::

        Assets
        ├── Cash and Cash Equivalents
        ├── Receivables from Financial Institutions
        ├── Loans and Advances
        │   └── Loan Loss Provision                ← contra
        ├── Assets at FVTPL (Trading Book)
        ├── Investment Securities                  ← composite
        │   ├── Investment Securities at Amortized Cost (HTM)
        │   └── Investment Securities at FVOCI
        ├── Property, Plant and Equipment
        └── Intangible Assets

        Liabilities
        ├── Deposits and Other Public Borrowings   ← composite
        │   ├── Deposits (Customer)
        │   └── Other Public Borrowings
        ├── Payables to Financial Institutions
        └── Debt Issues

        Equity
        ├── Shareholders' Equity
        └── Accumulated OCI                        ← composite
            ├── Unrealized OCI Gain
            └── Unrealized OCI Loss                ← contra

        Income
        ├── Interest Income                        ← composite
        ├── Trading Income (FVTPL)                 ← composite
        │   ├── Unrealized Trading Gain
        │   ├── Realized Trading Gain
        │   ├── Unrealized Trading Loss
        │   └── Realized Trading Loss
        └── Investment Income (FVOCI)              ← composite
            ├── Realized OCI Gain
            └── Realized OCI Loss

        Expenses
        ├── Interest Expense
        └── Operating Expense
    """

    def __init__(self) -> None:  # noqa: D107
        super().__init__()
        self._create_accounts()
        self._register_accounts()

    def _create_accounts(self) -> None:
        """Create all account instances and wire composites."""
        # ── Assets ───────────────────────────────────────────────────
        self.cash_account = TAccount("Cash and Cash Equivalents", AccountType.ASSET)
        self.receivable_account = TAccount("Receivables from Financial Institutions", AccountType.ASSET)

        self.loan_loss_provision_account = TAccount(
            "Loan Loss Provision", AccountType.ASSET, is_contra_account=True,
        )
        self.loan_account = TAccount(
            "Loans and Advances", AccountType.ASSET,
            contra_accounts=[self.loan_loss_provision_account],
        )
        self.asset_fvtpl_account = TAccount("Assets at FVTPL", AccountType.ASSET)

        self.investment_htm_account = TAccount("Investment Securities at Amortized Cost", AccountType.ASSET)
        self.investment_fvoci_account = TAccount("Investment Securities at FVOCI", AccountType.ASSET)
        self.investment_securities_account = CompositeTAccount("Investment Securities", AccountType.ASSET)
        self.investment_securities_account.add_sub_account(self.investment_htm_account)
        self.investment_securities_account.add_sub_account(self.investment_fvoci_account)

        self.ppe_account = TAccount("Property, Plant and Equipment", AccountType.ASSET)
        self.intangible_account = TAccount("Intangible Assets", AccountType.ASSET)
        self.accrued_interest_receivable = TAccount("Accrued Interest Receivable", AccountType.ASSET)

        # ── Liabilities ──────────────────────────────────────────────
        self.customer_deposits_account = TAccount("Deposits", AccountType.LIABILITY)
        self.public_borrowings_account = TAccount("Other Public Borrowings", AccountType.LIABILITY)
        self.deposit_account = CompositeTAccount("Deposits and Other Public Borrowings", AccountType.LIABILITY)
        self.deposit_account.add_sub_account(self.customer_deposits_account)
        self.deposit_account.add_sub_account(self.public_borrowings_account)

        self.interest_payable_account = TAccount("Interest Payable", AccountType.LIABILITY)
        self.payable_account = TAccount("Payables to Financial Institutions", AccountType.LIABILITY)
        self.debt_account = TAccount("Debt Issues", AccountType.LIABILITY)

        # ── Equity ───────────────────────────────────────────────────
        self.equity_account = TAccount("Shareholders' Equity", AccountType.EQUITY)

        self.unrealized_oci_loss_account = TAccount(
            "Unrealized OCI Loss", AccountType.EQUITY, is_contra_account=True,
        )
        self.unrealized_oci_gain_account = TAccount(
            "Unrealized OCI Gain", AccountType.EQUITY, contra_accounts=[self.unrealized_oci_loss_account],
        )
        self.accumulated_oci_account = CompositeTAccount("Accumulated OCI", AccountType.EQUITY)
        self.accumulated_oci_account.add_sub_account(self.unrealized_oci_gain_account)
        self.accumulated_oci_account.add_sub_account(self.unrealized_oci_loss_account)

        # ── Income ───────────────────────────────────────────────────
        self.interest_income_account = CompositeTAccount("Interest Income", AccountType.INCOME)

        self.unrealized_trading_gain_account = TAccount("Unrealized Trading Gain", AccountType.INCOME)
        self.realized_trading_gain_account = TAccount("Realized Trading Gain", AccountType.INCOME)
        self.unrealized_trading_loss_account = TAccount("Unrealized Trading Loss", AccountType.EXPENSE)
        self.realized_trading_loss_account = TAccount("Realized Trading Loss", AccountType.EXPENSE)
        self.trading_income_account = CompositeTAccount("Trading Income (FVTPL)", AccountType.INCOME)
        self.trading_income_account.add_sub_account(self.unrealized_trading_gain_account)
        self.trading_income_account.add_sub_account(self.realized_trading_gain_account)
        self.trading_income_account.add_sub_account(self.unrealized_trading_loss_account)
        self.trading_income_account.add_sub_account(self.realized_trading_loss_account)

        self.realized_oci_gain_account = TAccount("Realized OCI Gain", AccountType.INCOME)
        self.realized_oci_loss_account = TAccount("Realized OCI Loss", AccountType.EXPENSE)
        self.investment_income_account = CompositeTAccount("Investment Income (FVOCI)", AccountType.INCOME)
        self.investment_income_account.add_sub_account(self.realized_oci_gain_account)
        self.investment_income_account.add_sub_account(self.realized_oci_loss_account)

        # ── Expenses ─────────────────────────────────────────────────
        self.interest_expense_account = TAccount("Interest Expense", AccountType.EXPENSE)
        self.operating_expense_account = TAccount("Operating Expense", AccountType.EXPENSE)

    def _register_accounts(self) -> None:
        """Register all accounts using the builder for type validation."""
        builder = ChartOfAccountsBuilder()

        # Assets
        for acct in [
            self.cash_account, self.receivable_account, self.loan_account,
            self.asset_fvtpl_account, self.investment_securities_account,
            self.ppe_account, self.intangible_account, self.accrued_interest_receivable,
        ]:
            builder.add_asset_account(acct)

        # Liabilities
        for acct in [self.deposit_account, self.interest_payable_account, self.payable_account, self.debt_account]:
            builder.add_liability_account(acct)

        # Equity
        for acct in [self.equity_account, self.accumulated_oci_account]:
            builder.add_equity_account(acct)

        # Income
        for acct in [self.interest_income_account, self.trading_income_account, self.investment_income_account]:
            builder.add_income_account(acct)

        # Expenses
        for acct in [self.interest_expense_account, self.operating_expense_account]:
            builder.add_expense_account(acct)

        # Build validates types, then copy lists into self
        validated = builder.build()
        self.assets = validated.assets
        self.liabilities = validated.liabilities
        self.equities = validated.equities
        self.income = validated.income
        self.expenses = validated.expenses
