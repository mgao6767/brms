"""Tests for statement table models."""

# ruff: noqa: S101, D103, PLR2004

import copy

from PySide6.QtCore import Qt

from brms.app.models.statement_models import BalanceSheetModel, IncomeStatementModel, TrialBalanceModel
from brms.core.models.accounting.bank_accounts import BankChartOfAccounts
from brms.core.models.accounting.journal import Journal, SimpleEntry
from brms.core.models.accounting.ledger import Ledger


def test_trial_balance_model_empty() -> None:
    model = TrialBalanceModel()
    assert model.rowCount() == 0
    assert model.columnCount() == 3


def test_trial_balance_model_columns() -> None:
    model = TrialBalanceModel()
    assert model.headerData(0, Qt.Horizontal) == "Account"
    assert model.headerData(1, Qt.Horizontal) == "Debit"
    assert model.headerData(2, Qt.Horizontal) == "Credit"


def test_trial_balance_model_update() -> None:
    model = TrialBalanceModel()
    data = [
        {"account": "Cash", "debit": 1000.0, "credit": 0.0, "balance": 1000.0},
        {"account": "Equity", "debit": 0.0, "credit": 1000.0, "balance": 1000.0},
    ]
    model.update(data)
    # 2 account rows + 1 totals row
    assert model.rowCount() == 3
    # First row
    assert model.data(model.index(0, 0)) == "Cash"
    assert model.data(model.index(0, 1)) == 1000.0
    assert model.data(model.index(0, 2)) == 0.0
    # Totals row
    assert model.data(model.index(2, 0)) == "Total"
    assert model.data(model.index(2, 1)) == 1000.0
    assert model.data(model.index(2, 2)) == 1000.0


def test_trial_balance_model_skips_zero_rows() -> None:
    model = TrialBalanceModel()
    data = [
        {"account": "Cash", "debit": 1000.0, "credit": 0.0, "balance": 1000.0},
        {"account": "Empty", "debit": 0.0, "credit": 0.0, "balance": 0.0},
    ]
    model.update(data)
    # 1 account row + 1 totals row (zero row skipped)
    assert model.rowCount() == 2


def test_trial_balance_bold_role_on_totals() -> None:
    model = TrialBalanceModel()
    data = [
        {"account": "Cash", "debit": 100.0, "credit": 0.0, "balance": 100.0},
    ]
    model.update(data)
    # Row 0 (account) — not bold
    assert model.data(model.index(0, 0), Qt.UserRole) is not True
    # Row 1 (totals) — bold
    assert model.data(model.index(1, 0), Qt.UserRole) is True


def test_trial_balance_model_update_clears_old_data() -> None:
    model = TrialBalanceModel()
    data1 = [{"account": "Cash", "debit": 100.0, "credit": 0.0, "balance": 100.0}]
    model.update(data1)
    assert model.rowCount() == 2  # 1 + totals
    data2 = [
        {"account": "A", "debit": 1.0, "credit": 0.0, "balance": 1.0},
        {"account": "B", "debit": 0.0, "credit": 1.0, "balance": 1.0},
    ]
    model.update(data2)
    assert model.rowCount() == 3  # 2 + totals
    assert model.data(model.index(0, 0)) == "A"


def _make_ledger() -> tuple[Ledger, BankChartOfAccounts]:
    coa = BankChartOfAccounts()
    ledger = Ledger(chart_of_accounts=coa, journal=Journal())
    # Equity issuance
    ledger.post(
        SimpleEntry(
            debit_account=coa.cash_account,
            credit_account=coa.equity_account,
            value=1_000_000.0,
            date=None,
            description="Equity",
        ),
    )
    # Deposit
    ledger.post(
        SimpleEntry(
            debit_account=coa.cash_account,
            credit_account=coa.customer_deposits_account,
            value=500_000.0,
            date=None,
            description="Deposit",
        ),
    )
    # Buy HTM bond
    ledger.post(
        SimpleEntry(
            debit_account=coa.investment_htm_account,
            credit_account=coa.cash_account,
            value=200_000.0,
            date=None,
            description="Buy HTM",
        ),
    )
    return ledger, coa


def test_balance_sheet_model_columns() -> None:
    model = BalanceSheetModel()
    assert model.headerData(0, Qt.Horizontal) == "Account"
    assert model.headerData(1, Qt.Horizontal) == "Balance"


def test_balance_sheet_model_has_three_sections() -> None:
    ledger, _ = _make_ledger()
    closed = copy.deepcopy(ledger)
    model = BalanceSheetModel()
    model.update(closed.chart_of_accounts)
    # Root rows: Assets, Liabilities, Equity
    assert model.rowCount() == 3
    assert model.data(model.index(0, 0)) == "Assets"
    assert model.data(model.index(1, 0)) == "Liabilities"
    assert model.data(model.index(2, 0)) == "Equity"


def test_balance_sheet_model_section_headers_are_bold() -> None:
    ledger, _ = _make_ledger()
    closed = copy.deepcopy(ledger)
    model = BalanceSheetModel()
    model.update(closed.chart_of_accounts)
    for row in range(3):
        assert model.data(model.index(row, 0), Qt.UserRole) is True


def test_balance_sheet_model_assets_have_children() -> None:
    ledger, _ = _make_ledger()
    closed = copy.deepcopy(ledger)
    model = BalanceSheetModel()
    model.update(closed.chart_of_accounts)
    assets_idx = model.index(0, 0)
    # Should have child rows (accounts with non-zero balances + totals row)
    child_count = model.rowCount(assets_idx)
    assert child_count >= 2  # at least Cash + Total Assets


def test_balance_sheet_model_composite_has_children() -> None:
    """Investment Securities (composite) should expand to show HTM child."""
    ledger, _ = _make_ledger()
    closed = copy.deepcopy(ledger)
    model = BalanceSheetModel()
    model.update(closed.chart_of_accounts)
    assets_idx = model.index(0, 0)
    # Find Investment Securities row
    found = False
    for row in range(model.rowCount(assets_idx)):
        idx = model.index(row, 0, assets_idx)
        if model.data(idx) == "Investment Securities":
            found = True
            # Should have at least HTM child with non-zero balance
            assert model.rowCount(idx) >= 1
            break
    assert found, "Investment Securities row not found"


def test_balance_sheet_totals_row() -> None:
    ledger, _ = _make_ledger()
    closed = copy.deepcopy(ledger)
    model = BalanceSheetModel()
    model.update(closed.chart_of_accounts)
    assets_idx = model.index(0, 0)
    child_count = model.rowCount(assets_idx)
    # Last child of Assets section is "Total Assets" (bold)
    totals_idx = model.index(child_count - 1, 0, assets_idx)
    assert model.data(totals_idx) == "Total Assets"
    assert model.data(totals_idx, Qt.UserRole) is True
    totals_val = model.data(model.index(child_count - 1, 1, assets_idx))
    assert totals_val == 1_500_000.0  # Cash 1.3M + HTM 200k = 1.5M


def test_balance_sheet_skips_zero_accounts() -> None:
    """Accounts with zero balance should not appear."""
    ledger, _ = _make_ledger()
    closed = copy.deepcopy(ledger)
    model = BalanceSheetModel()
    model.update(closed.chart_of_accounts)
    assets_idx = model.index(0, 0)
    # PPE has zero balance — should not appear
    for row in range(model.rowCount(assets_idx)):
        idx = model.index(row, 0, assets_idx)
        assert model.data(idx) != "Property, Plant and Equipment"


def _make_ledger_with_income() -> tuple[Ledger, BankChartOfAccounts]:
    coa = BankChartOfAccounts()
    ledger = Ledger(chart_of_accounts=coa, journal=Journal())
    # Equity
    ledger.post(
        SimpleEntry(
            debit_account=coa.cash_account,
            credit_account=coa.equity_account,
            value=1_000_000.0,
            date=None,
            description="Equity",
        ),
    )
    # Interest income
    ledger.post(
        SimpleEntry(
            debit_account=coa.cash_account,
            credit_account=coa.interest_income_account,
            value=5_000.0,
            date=None,
            description="Interest received",
        ),
    )
    # Interest expense
    ledger.post(
        SimpleEntry(
            debit_account=coa.interest_expense_account,
            credit_account=coa.cash_account,
            value=2_000.0,
            date=None,
            description="Interest paid",
        ),
    )
    return ledger, coa


def test_income_statement_model_columns() -> None:
    model = IncomeStatementModel()
    assert model.headerData(0, Qt.Horizontal) == "Account"
    assert model.headerData(1, Qt.Horizontal) == "Balance"


def test_income_statement_model_has_sections() -> None:
    ledger, _ = _make_ledger_with_income()
    model = IncomeStatementModel()
    model.update(ledger.chart_of_accounts)
    # Root rows: Income, Expenses, Net Income
    assert model.rowCount() == 3
    assert model.data(model.index(0, 0)) == "Income"
    assert model.data(model.index(1, 0)) == "Expenses"
    assert model.data(model.index(2, 0)) == "Net Income"


def test_income_statement_model_net_income() -> None:
    ledger, _ = _make_ledger_with_income()
    model = IncomeStatementModel()
    model.update(ledger.chart_of_accounts)
    net_income_idx = model.index(2, 1)
    assert model.data(net_income_idx) == 3_000.0  # 5000 - 2000


def test_income_statement_model_income_children() -> None:
    ledger, _ = _make_ledger_with_income()
    model = IncomeStatementModel()
    model.update(ledger.chart_of_accounts)
    income_idx = model.index(0, 0)
    # Should have at least Interest Income + Total Income
    assert model.rowCount(income_idx) >= 2


def test_income_statement_model_totals_bold() -> None:
    ledger, _ = _make_ledger_with_income()
    model = IncomeStatementModel()
    model.update(ledger.chart_of_accounts)
    # Net Income row should be bold
    assert model.data(model.index(2, 0), Qt.UserRole) is True
    # Income section header should be bold
    assert model.data(model.index(0, 0), Qt.UserRole) is True
