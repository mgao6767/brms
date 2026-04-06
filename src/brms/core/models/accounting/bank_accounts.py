"""Pre-configured chart of accounts for a commercial bank.

All bank-specific accounts are created as plain ``TAccount`` or
``CompositeTAccount`` instances — no subclasses needed.  The
:class:`BankChartOfAccounts` wires them together and exposes each
account as a named attribute.
"""

from __future__ import annotations

from brms.core.models.accounting.accounts import AccountType, CompositeTAccount, TAccount
from brms.core.models.accounting.chart_of_accounts import ChartOfAccounts


class BankChartOfAccounts(ChartOfAccounts):
    """Pre-configured chart of accounts for a commercial bank.

    Every account is accessible as a named attribute.  Composite accounts
    automatically aggregate their sub-accounts.

    Account hierarchy::

        Assets
        ├── Cash and Cash Equivalents
        ├── Receivables from Financial Institutions
        ├── Loans and Advances
        ├── Assets at FVTPL (Trading Book)
        ├── Investment Securities          ← composite
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
            └── Unrealized OCI Loss (contra)

        Income
        ├── Interest Income
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

    def __init__(self) -> None:
        super().__init__()

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
        self.investment_securities_account.add(self.investment_htm_account)
        self.investment_securities_account.add(self.investment_fvoci_account)

        self.ppe_account = TAccount("Property, Plant and Equipment", AccountType.ASSET)
        self.intangible_account = TAccount("Intangible Assets", AccountType.ASSET)

        # ── Liabilities ──────────────────────────────────────────────
        self.customer_deposits_account = TAccount("Deposits", AccountType.LIABILITY)
        self.public_borrowings_account = TAccount("Other Public Borrowings", AccountType.LIABILITY)
        self.deposit_account = CompositeTAccount("Deposits and Other Public Borrowings", AccountType.LIABILITY)
        self.deposit_account.add(self.customer_deposits_account)
        self.deposit_account.add(self.public_borrowings_account)

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
        self.accumulated_oci_account.add(self.unrealized_oci_gain_account)
        self.accumulated_oci_account.add(self.unrealized_oci_loss_account)

        # ── Income ───────────────────────────────────────────────────
        self.interest_income_account = CompositeTAccount("Interest Income", AccountType.INCOME)

        self.unrealized_trading_gain_account = TAccount("Unrealized Trading Gain", AccountType.INCOME)
        self.realized_trading_gain_account = TAccount("Realized Trading Gain", AccountType.INCOME)
        self.unrealized_trading_loss_account = TAccount("Unrealized Trading Loss", AccountType.EXPENSE)
        self.realized_trading_loss_account = TAccount("Realized Trading Loss", AccountType.EXPENSE)
        self.trading_income_account = CompositeTAccount("Trading Income (FVTPL)", AccountType.INCOME)
        self.trading_income_account.add(self.unrealized_trading_gain_account)
        self.trading_income_account.add(self.realized_trading_gain_account)
        self.trading_income_account.add(self.unrealized_trading_loss_account)
        self.trading_income_account.add(self.realized_trading_loss_account)

        self.realized_oci_gain_account = TAccount("Realized OCI Gain", AccountType.INCOME)
        self.realized_oci_loss_account = TAccount("Realized OCI Loss", AccountType.EXPENSE)
        self.investment_income_account = CompositeTAccount("Investment Income (FVOCI)", AccountType.INCOME)
        self.investment_income_account.add(self.realized_oci_gain_account)
        self.investment_income_account.add(self.realized_oci_loss_account)

        # ── Expenses ─────────────────────────────────────────────────
        self.interest_expense_account = TAccount("Interest Expense", AccountType.EXPENSE)
        self.operating_expense_account = TAccount("Operating Expense", AccountType.EXPENSE)

        # ── Register in parent ChartOfAccounts ───────────────────────
        self.assets.extend([
            self.cash_account, self.receivable_account, self.loan_account,
            self.asset_fvtpl_account, self.investment_securities_account,
            self.ppe_account, self.intangible_account,
        ])
        self.liabilities.extend([self.deposit_account, self.payable_account, self.debt_account])
        self.equities.extend([self.equity_account, self.accumulated_oci_account])
        self.income.extend([self.interest_income_account, self.trading_income_account, self.investment_income_account])
        self.expenses.extend([self.interest_expense_account, self.operating_expense_account])
