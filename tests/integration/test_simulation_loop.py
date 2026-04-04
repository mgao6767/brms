"""Integration tests for the full simulation loop with step-back."""

import json
import zipfile
from io import BytesIO

from brms.core.events import EventBus
from brms.core.metrics.base import MetricRegistry
from brms.core.models.accounting.rules.base import RuleRegistry
from brms.core.models.accounting.service import AccountingService
from brms.core.models.history import SimulationHistory
from brms.core.services.data_service import DataService
from brms.core.services.metrics_service import MetricsService
from brms.core.services.simulation_service import SimulationService


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


def test_full_simulation_loop() -> None:
    """End-to-end: load, advance 3 days, step back 1, advance again."""
    bank, store = DataService().load_simulation_from_buffer(_create_test_zip())
    history = SimulationHistory()
    service = SimulationService(
        bank=bank,
        market_data=store,
        rule_registry=RuleRegistry(),
        accounting_service=AccountingService(),
        metrics_service=MetricsService(MetricRegistry()),
        history=history,
        event_bus=EventBus(),
    )

    # Advance 3 days
    for _ in range(3):
        service.advance()
    assert len(history.dates) == 3  # noqa: PLR2004, S101
    date_after_3 = service.current_date

    # Step back 1
    service.step_back()
    assert len(history.dates) == 2  # noqa: PLR2004, S101
    assert service.current_date < date_after_3  # noqa: S101

    # Advance again
    service.advance()
    assert len(history.dates) == 3  # noqa: PLR2004, S101


def test_events_emitted() -> None:
    """Verify DateAdvanced and DateReverted events are emitted."""
    from brms.core.events import DateAdvanced, DateReverted

    bank, store = DataService().load_simulation_from_buffer(_create_test_zip())
    history = SimulationHistory()
    event_bus = EventBus()
    advanced: list[DateAdvanced] = []
    reverted: list[DateReverted] = []
    event_bus.subscribe(DateAdvanced, lambda e: advanced.append(e))
    event_bus.subscribe(DateReverted, lambda e: reverted.append(e))

    service = SimulationService(
        bank=bank,
        market_data=store,
        rule_registry=RuleRegistry(),
        accounting_service=AccountingService(),
        metrics_service=MetricsService(MetricRegistry()),
        history=history,
        event_bus=event_bus,
    )
    service.advance()
    service.advance()
    service.step_back()

    assert len(advanced) == 2  # noqa: PLR2004, S101
    assert len(reverted) == 1  # noqa: S101


def test_sample_zip_loads() -> None:
    """Verify the sample simulation zip fixture loads correctly."""
    from pathlib import Path

    from brms.core.services.data_service import DataService

    service = DataService()
    bank, store = service.load_simulation(Path("tests/fixtures/sample_simulation.zip"))
    assert bank.name == "Sample Bank"  # noqa: S101
    assert len(store.available_dates()) == 30  # noqa: PLR2004, S101


def test_simulation_with_rules_and_accounting() -> None:
    """Full simulation with registered rules, AccountingService, and real ledger."""
    import datetime
    import json
    import zipfile
    from io import BytesIO

    from brms.core.events import EventBus
    from brms.core.metrics.base import MetricRegistry
    from brms.core.models.accounting.accounts import BankChartOfAccounts
    from brms.core.models.accounting.journal import Journal
    from brms.core.models.accounting.ledger import Ledger
    from brms.core.models.accounting.rules.amortization import AmortizationRule
    from brms.core.models.accounting.rules.base import RuleRegistry
    from brms.core.models.accounting.rules.coupon import CouponPaymentRule
    from brms.core.models.accounting.rules.interest import InterestPaymentRule
    from brms.core.models.accounting.rules.mark_to_market import MarkToMarketRule
    from brms.core.models.accounting.rules.maturity import MaturityRule
    from brms.core.models.accounting.service import AccountingService
    from brms.core.models.history import SimulationHistory
    from brms.core.services.data_service import DataService
    from brms.core.services.metrics_service import MetricsService
    from brms.core.services.simulation_service import SimulationService

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

    history = SimulationHistory()
    service = SimulationService(
        bank=bank,
        market_data=store,
        rule_registry=rule_registry,
        accounting_service=AccountingService(),
        metrics_service=MetricsService(MetricRegistry()),
        history=history,
        event_bus=EventBus(),
    )

    # Advance 5 days
    for _ in range(5):
        service.advance()
    assert len(history.dates) == 5  # noqa: PLR2004, S101
    assert service.current_date == datetime.date(2024, 1, 5)  # noqa: S101

    # Step back 2
    service.step_back()
    service.step_back()
    assert len(history.dates) == 3  # noqa: PLR2004, S101
    assert service.current_date == datetime.date(2024, 1, 3)  # noqa: S101

    # Advance 3 more
    for _ in range(3):
        service.advance()
    assert len(history.dates) == 6  # noqa: PLR2004, S101
