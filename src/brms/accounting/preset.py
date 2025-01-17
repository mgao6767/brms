"""Defines preset accounts for a bank's accounting system."""

from brms.accounting.account import AccountType, ChartOfAccountsBuilder, CompositeTAccount, TAccount

__all__ = [  # noqa: RUF022
    "cash_account",
    "receivable_account",
    "loan_account",
    "asset_fvtpl_account",
    "investment_securities_account",
    "investment_htm_account",
    "investment_fvoci_account",
    "ppe_account",
    "intangible_account",
    "deposit_account",
    "customer_deposit_account",
    "public_borrowings_account",
    "payable_account",
    "debt_account",
    "equity_account",
    "interest_income_account",
    "trading_income_account",
    "interest_expense_account",
    "operating_expense_account",
    "chart_of_accounts",
]

builder = ChartOfAccountsBuilder()

# =========== Asset accounts ===========
# fmt: off
# Cash
cash_account = TAccount("Cash and Cash Equivalents", AccountType.ASSET)
# Receivables
receivable_account = TAccount("Receivables from Financial Institutions", AccountType.ASSET)
# Loans provided to customers that the bank intends to hold until maturity and collect principal and interest.
# - banking book only
loan_account = TAccount("Loans and Advances", AccountType.ASSET)
# Assets at Fair Value Through Income Statement (FVTPL)
# - Trading Book securities
asset_fvtpl_account = TAccount("Assets at Fair Value Through Income Statement (FVTPL)", AccountType.ASSET)
# Investment Securities
investment_securities_account = CompositeTAccount("Invest Securities", AccountType.ASSET)
# Investment Securities at Amortized Cost (HTM - Held to Maturity)
# Debt securities (bonds, treasuries) that the bank intends to hold until maturity.
# - Banking Book only
# - No fair value adjustments unless impaired.
investment_htm_account = TAccount("Investment Securities at Amortized Cost", AccountType.ASSET)
investment_securities_account.add(investment_htm_account)
# Investment Securities at Fair Value Through Other Comprehensive Income (FVOCI)
# - Banking Book: Some debt securities where the bank intends to collect cash flows and sell occasionally.
# - Changes in fair value are recorded in OCI, not P&L, until sale.
investment_fvoci_account = TAccount("Investment Securities at Fair Value Through Other Comprehensive Income (FVOCI)", AccountType.ASSET)
investment_securities_account.add(investment_fvoci_account)
# PPE
ppe_account = TAccount("Property, Plant and Equipment", AccountType.ASSET)
# Intangible
intangible_account = TAccount("Intangible Assets", AccountType.ASSET)
# fmt: on

builder.add_asset_account(cash_account)
builder.add_asset_account(receivable_account)
builder.add_asset_account(loan_account)
builder.add_asset_account(asset_fvtpl_account)
builder.add_asset_account(investment_securities_account)
builder.add_asset_account(ppe_account)
builder.add_asset_account(intangible_account)

# =========== Liability accounts ===========
# Deposits and other public borrowings
deposit_account = CompositeTAccount("Deposits and Other Public Borrowings", AccountType.LIABILITY)
# Deposits
customer_deposit_account = TAccount("Deposits", AccountType.LIABILITY)
deposit_account.add(customer_deposit_account)
# Other public borrowings (typically short-term)
public_borrowings_account = TAccount("Other Public Borrowings", AccountType.LIABILITY)
deposit_account.add(public_borrowings_account)
# Payables
payable_account = TAccount("Payables to Financial Institutions", AccountType.LIABILITY)
# Debt issues (typically long-term)
debt_account = TAccount("Debt Issues", AccountType.LIABILITY)

builder.add_liability_account(deposit_account)
builder.add_liability_account(payable_account)
builder.add_liability_account(debt_account)

# =========== Equity accounts ===========
equity_account = TAccount("Shareholders' Equity", AccountType.EQUITY)
builder.add_equity_account(equity_account)

# =========== Income accounts ===========
# For Income Statement
interest_income_account = CompositeTAccount("Interest Income", AccountType.INCOME)
builder.add_income_account(interest_income_account)
# For Other Comprehensive Income (OCI)
# TODO: OCI statement
trading_income_account = TAccount("Trading Income", AccountType.INCOME)
builder.add_income_account(trading_income_account)

# =========== Expense accounts ===========
interest_expense_account = TAccount("Interest Expense", AccountType.EXPENSE)
operating_expense_account = TAccount("Operating Expense", AccountType.EXPENSE)
builder.add_expense_account(interest_expense_account)
builder.add_expense_account(operating_expense_account)


chart_of_accounts = builder.build()
