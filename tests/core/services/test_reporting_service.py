"""Tests for ReportingService."""

from brms.core.models.accounting.bank_accounts import BankChartOfAccounts
from brms.core.models.accounting.journal import Journal, SimpleEntry
from brms.core.models.accounting.ledger import Ledger
from brms.core.services.reporting_service import ReportingService


def _make_ledger_with_data() -> tuple[Ledger, BankChartOfAccounts]:
    coa = BankChartOfAccounts()
    journal = Journal()
    ledger = Ledger(chart_of_accounts=coa, journal=journal)
    # Equity issuance: debit cash, credit equity
    ledger.post(
        SimpleEntry(
            debit_account=coa.cash_account,
            credit_account=coa.equity_account,
            value=1000000.0,
            date=None,
            description="Equity",
        )
    )
    # Deposit: debit cash, credit deposits
    ledger.post(
        SimpleEntry(
            debit_account=coa.cash_account,
            credit_account=coa.customer_deposits_account,
            value=500000.0,
            date=None,
            description="Deposit",
        )
    )
    return ledger, coa


def test_trial_balance_returns_list() -> None:
    ledger, _ = _make_ledger_with_data()
    result = ReportingService().trial_balance(ledger)
    assert isinstance(result, list)
    assert len(result) > 0
    assert "account" in result[0]


def test_trial_balance_row_has_expected_keys() -> None:
    ledger, _ = _make_ledger_with_data()
    result = ReportingService().trial_balance(ledger)
    for row in result:
        assert "account" in row
        assert "debit" in row
        assert "credit" in row
        assert "balance" in row


def test_balance_sheet_has_totals() -> None:
    ledger, _ = _make_ledger_with_data()
    bs = ReportingService().balance_sheet(ledger)
    assert bs["total_assets"] == 1500000.0
    assert bs["total_liabilities"] == 500000.0
    assert bs["total_equity"] == 1000000.0


def test_balance_sheet_balances() -> None:
    ledger, _ = _make_ledger_with_data()
    bs = ReportingService().balance_sheet(ledger)
    assert abs(bs["total_assets"] - bs["total_liabilities"] - bs["total_equity"]) < 0.01


def test_balance_sheet_has_lists() -> None:
    ledger, _ = _make_ledger_with_data()
    bs = ReportingService().balance_sheet(ledger)
    assert "assets" in bs
    assert "liabilities" in bs
    assert "equity" in bs
    assert isinstance(bs["assets"], list)
    assert isinstance(bs["liabilities"], list)
    assert isinstance(bs["equity"], list)


def test_income_statement_structure() -> None:
    ledger, _ = _make_ledger_with_data()
    result = ReportingService().income_statement(ledger)
    assert "net_income" in result


def test_income_statement_has_lists() -> None:
    ledger, _ = _make_ledger_with_data()
    result = ReportingService().income_statement(ledger)
    assert "income" in result
    assert "expenses" in result
    assert "total_income" in result
    assert "total_expenses" in result
    assert isinstance(result["income"], list)
    assert isinstance(result["expenses"], list)


def test_income_statement_net_income_is_zero_with_no_transactions() -> None:
    ledger, _ = _make_ledger_with_data()
    result = ReportingService().income_statement(ledger)
    # No income/expense transactions were posted in the fixture
    assert result["net_income"] == 0.0
