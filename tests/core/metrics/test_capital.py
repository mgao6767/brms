"""Tests for capital metrics."""

from unittest.mock import MagicMock

from brms.core.metrics.capital import CET1RatioMetric, TotalAssetsMetric, TotalEquityMetric, TotalLiabilitiesMetric
from brms.core.models.accounting.bank_accounts import BankChartOfAccounts
from brms.core.models.accounting.journal import Journal, SimpleEntry
from brms.core.models.accounting.ledger import Ledger
from brms.core.models.bank import Bank
from brms.core.services.reporting_service import ReportingService
from brms.core.stores.instrument_store import InstrumentStore
from brms.core.stores.position_store import PositionStore

_EQUITY = 1000000.0
_DEPOSIT = 500000.0
_TOTAL_ASSETS = _EQUITY + _DEPOSIT
_TOLERANCE = 1e-9

_reporting = ReportingService()


def _make_bank() -> Bank:
    coa = BankChartOfAccounts()
    ledger = Ledger(chart_of_accounts=coa, journal=Journal())
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
    return Bank(name="Test", instruments=InstrumentStore(), positions=PositionStore(), ledger=ledger)


def test_total_assets() -> None:  # noqa: D103
    bank = _make_bank()
    assert TotalAssetsMetric(_reporting).compute(bank, None, MagicMock()) == _TOTAL_ASSETS  # noqa: S101


def test_total_liabilities() -> None:  # noqa: D103
    bank = _make_bank()
    assert TotalLiabilitiesMetric(_reporting).compute(bank, None, MagicMock()) == _DEPOSIT  # noqa: S101


def test_total_equity() -> None:  # noqa: D103
    bank = _make_bank()
    assert TotalEquityMetric(_reporting).compute(bank, None, MagicMock()) == _EQUITY  # noqa: S101


def test_cet1_ratio() -> None:  # noqa: D103
    bank = _make_bank()
    ratio = CET1RatioMetric(_reporting).compute(bank, None, MagicMock())
    assert abs(ratio - _EQUITY / _TOTAL_ASSETS) < _TOLERANCE  # noqa: S101
