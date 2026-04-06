"""Integration tests for the full simulation loop with step-back."""

import json
import zipfile
from io import BytesIO

from brms.core.events import EventBus
from brms.core.metrics.base import MetricRegistry
from brms.core.models.accounting.rules.base import RuleRegistry
from brms.core.models.accounting.service import AccountingService
from brms.core.services.data_service import DataService
from brms.core.services.metrics_service import MetricsService
from brms.core.services.simulation_service import LegacySimulationService, SimulationHistory


def _create_test_zip() -> BytesIO:
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        bank_data = {
            "name": "Integration Test Bank",
            "as_of_date": "2024-01-01",
            "banking_book": [],
            "trading_book": [],
            "initial_accounts": {"cash": 5000000},
        }
        zf.writestr("bank.json", json.dumps(bank_data))
        csv = "date,1Y,5Y,10Y\n"
        for i in range(1, 6):
            csv += f"2024-01-{i:02d},0.04,0.045,0.05\n"
        zf.writestr("yields.csv", csv)
    buf.seek(0)
    return buf


def _make_legacy_service(bank, store, event_bus=None, rule_registry=None):  # noqa: ANN001, ANN202
    """Build a LegacySimulationService from a v2 Bank and store."""
    from unittest.mock import MagicMock

    # Wrap the v2 bank to have legacy attributes
    legacy_bank = MagicMock()
    legacy_bank.name = bank.name
    legacy_bank.banking_book = bank.banking_book
    legacy_bank.trading_book = bank.trading_book
    legacy_bank.ledger = bank.ledger

    return LegacySimulationService(
        bank=legacy_bank,
        market_data=store,
        rule_registry=rule_registry or RuleRegistry(),
        accounting_service=AccountingService(),
        metrics_service=MetricsService(MetricRegistry()),
        history=SimulationHistory(),
        event_bus=event_bus or EventBus(),
    )


def test_full_simulation_loop() -> None:
    """End-to-end: load, advance 3 days, step back 1, advance again."""
    bank, store = DataService().load_simulation_from_buffer(_create_test_zip())
    service = _make_legacy_service(bank, store)

    # Advance 3 days
    for _ in range(3):
        service.advance()
    assert len(service.history.dates) == 3  # noqa: PLR2004, S101
    date_after_3 = service.current_date

    # Step back 1
    service.step_back()
    assert len(service.history.dates) == 2  # noqa: PLR2004, S101
    assert service.current_date < date_after_3  # noqa: S101

    # Advance again
    service.advance()
    assert len(service.history.dates) == 3  # noqa: PLR2004, S101


def test_events_emitted() -> None:
    """Verify DateAdvanced and DateReverted events are emitted."""
    from brms.core.events import DateAdvanced, DateReverted

    bank, store = DataService().load_simulation_from_buffer(_create_test_zip())
    event_bus = EventBus()
    advanced: list[DateAdvanced] = []
    reverted: list[DateReverted] = []
    event_bus.subscribe(DateAdvanced, lambda e: advanced.append(e))
    event_bus.subscribe(DateReverted, lambda e: reverted.append(e))

    service = _make_legacy_service(bank, store, event_bus=event_bus)
    service.advance()
    service.advance()
    service.step_back()

    assert len(advanced) == 2  # noqa: PLR2004, S101
    assert len(reverted) == 1  # noqa: S101


def test_sample_zip_loads() -> None:
    """Verify the sample simulation zip fixture loads correctly."""
    from pathlib import Path

    service = DataService()
    bank, store = service.load_simulation(Path("tests/fixtures/sample_simulation.zip"))
    assert bank.name == "Sample Bank"  # noqa: S101
    assert len(store.available_dates()) == 30  # noqa: PLR2004, S101


def test_simulation_with_rules_and_accounting() -> None:
    """Full simulation with registered rules, AccountingService, and real ledger."""
    import datetime

    from brms.core.models.accounting.accounts import BankChartOfAccounts
    from brms.core.models.accounting.journal import Journal
    from brms.core.models.accounting.ledger import Ledger
    from brms.core.models.accounting.rules.amortization import AmortizationRule
    from brms.core.models.accounting.rules.coupon import CouponPaymentRule
    from brms.core.models.accounting.rules.interest import InterestPaymentRule
    from brms.core.models.accounting.rules.mark_to_market import MarkToMarketRule
    from brms.core.models.accounting.rules.maturity import MaturityRule

    # Create zip
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(
            "bank.json",
            json.dumps({
                "name": "Full Test Bank",
                "as_of_date": "2024-01-01",
                "banking_book": [],
                "trading_book": [],
                "initial_accounts": {"cash": 10000000},
            }),
        )
        csv = "date,1Y,5Y\n"
        for i in range(1, 11):
            csv += f"2024-01-{i:02d},0.04,0.045\n"
        zf.writestr("yields.csv", csv)
    buf.seek(0)

    # Load
    bank, store = DataService().load_simulation_from_buffer(buf)

    # Give bank a real ledger
    coa = BankChartOfAccounts()
    journal = Journal()
    ledger = Ledger(journal=journal, chart_of_accounts=coa)
    bank.ledger = ledger

    # Register rules
    rule_registry = RuleRegistry()
    rule_registry.register(MaturityRule())
    rule_registry.register(CouponPaymentRule())
    rule_registry.register(InterestPaymentRule())
    rule_registry.register(MarkToMarketRule())
    rule_registry.register(AmortizationRule())

    service = _make_legacy_service(bank, store, rule_registry=rule_registry)

    # Advance 5 days
    for _ in range(5):
        service.advance()
    assert len(service.history.dates) == 5  # noqa: PLR2004, S101
    assert service.current_date == datetime.date(2024, 1, 5)  # noqa: S101

    # Step back 2
    service.step_back()
    service.step_back()
    assert len(service.history.dates) == 3  # noqa: PLR2004, S101
    assert service.current_date == datetime.date(2024, 1, 3)  # noqa: S101

    # Advance 3 more
    for _ in range(3):
        service.advance()
    assert len(service.history.dates) == 6  # noqa: PLR2004, S101


def test_simulation_with_reporting() -> None:
    """Full simulation with reporting service generating financial statements."""
    from brms.core.models.accounting.accounts import BankChartOfAccounts
    from brms.core.models.accounting.journal import Journal
    from brms.core.models.accounting.ledger import Ledger
    from brms.core.services.reporting_service import ReportingService

    buf = BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("bank.json", json.dumps({
            "name": "Report Test Bank",
            "as_of_date": "2024-01-01",
            "banking_book": [],
            "trading_book": [],
            "initial_accounts": {"cash": 10000000},
        }))
        csv = "date,1Y,5Y\n"
        for i in range(1, 6):
            csv += f"2024-01-{i:02d},0.04,0.045\n"
        zf.writestr("yields.csv", csv)
    buf.seek(0)

    bank, store = DataService().load_simulation_from_buffer(buf)
    coa = BankChartOfAccounts()
    ledger = Ledger(chart_of_accounts=coa, journal=Journal())
    bank.ledger = ledger

    service = _make_legacy_service(bank, store)
    service.advance()

    reporting = ReportingService()
    bs = reporting.balance_sheet(bank.ledger)
    assert "total_assets" in bs  # noqa: S101
    assert "total_liabilities" in bs  # noqa: S101
    assert "total_equity" in bs  # noqa: S101

    is_data = reporting.income_statement(bank.ledger)
    assert "net_income" in is_data  # noqa: S101

    tb = reporting.trial_balance(bank.ledger)
    assert isinstance(tb, list)  # noqa: S101
    assert len(tb) > 0  # noqa: S101
