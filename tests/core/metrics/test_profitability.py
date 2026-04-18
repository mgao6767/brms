"""Tests for profitability metrics (ROA, ROE)."""

from unittest.mock import MagicMock

from brms.core.metrics.profitability import ROAMetric, ROEMetric
from brms.core.models.accounting.bank_accounts import BankChartOfAccounts
from brms.core.models.accounting.journal import Journal, SimpleEntry
from brms.core.models.accounting.ledger import Ledger
from brms.core.models.bank import Bank
from brms.core.services.reporting_service import ReportingService
from brms.core.stores.instrument_store import InstrumentStore
from brms.core.stores.position_store import PositionStore

_EQUITY = 1_000_000.0
_DEPOSIT = 500_000.0
_INTEREST_INCOME = 50_000.0
_INTEREST_EXPENSE = 20_000.0
_NET_INCOME = _INTEREST_INCOME - _INTEREST_EXPENSE
_TOTAL_ASSETS = _EQUITY + _DEPOSIT
_TOLERANCE = 1e-9

_reporting = ReportingService()


def _make_bank() -> Bank:
    coa = BankChartOfAccounts()
    ledger = Ledger(chart_of_accounts=coa, journal=Journal())
    # Fund the bank: equity + deposits → cash
    ledger.post(
        SimpleEntry(
            debit_account=coa.cash_account,
            credit_account=coa.equity_account,
            value=_EQUITY,
            date=None,
            description="Equity",
        ),
    )
    ledger.post(
        SimpleEntry(
            debit_account=coa.cash_account,
            credit_account=coa.customer_deposits_account,
            value=_DEPOSIT,
            date=None,
            description="Deposit",
        ),
    )
    # Interest earned on assets
    ledger.post(
        SimpleEntry(
            debit_account=coa.cash_account,
            credit_account=coa.interest_income_account,
            value=_INTEREST_INCOME,
            date=None,
            description="Interest income",
        ),
    )
    # Interest paid on deposits
    ledger.post(
        SimpleEntry(
            debit_account=coa.interest_expense_account,
            credit_account=coa.cash_account,
            value=_INTEREST_EXPENSE,
            date=None,
            description="Interest expense",
        ),
    )
    return Bank(name="Test", instruments=InstrumentStore(), positions=PositionStore(), ledger=ledger)


def test_roa() -> None:
    """ROA = net income / total assets."""
    bank = _make_bank()
    # Total assets = cash (equity + deposit + income - expense) = 1_530_000
    expected_assets = _EQUITY + _DEPOSIT + _INTEREST_INCOME - _INTEREST_EXPENSE
    roa = ROAMetric(_reporting).compute(bank, None, MagicMock())
    assert abs(roa - _NET_INCOME / expected_assets) < _TOLERANCE  # noqa: S101


def test_roe() -> None:
    """ROE = net income / total equity."""
    bank = _make_bank()
    roe = ROEMetric(_reporting).compute(bank, None, MagicMock())
    assert abs(roe - _NET_INCOME / _EQUITY) < _TOLERANCE  # noqa: S101


def test_roa_zero_assets() -> None:
    """ROA returns 0.0 when total assets are zero."""
    coa = BankChartOfAccounts()
    ledger = Ledger(chart_of_accounts=coa, journal=Journal())
    bank = Bank(name="Empty", instruments=InstrumentStore(), positions=PositionStore(), ledger=ledger)
    assert ROAMetric(_reporting).compute(bank, None, MagicMock()) == 0.0  # noqa: S101


def test_roe_zero_equity() -> None:
    """ROE returns 0.0 when total equity is zero."""
    coa = BankChartOfAccounts()
    ledger = Ledger(chart_of_accounts=coa, journal=Journal())
    bank = Bank(name="Empty", instruments=InstrumentStore(), positions=PositionStore(), ledger=ledger)
    assert ROEMetric(_reporting).compute(bank, None, MagicMock()) == 0.0  # noqa: S101
