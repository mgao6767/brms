"""Tests for LegacySimulationService: advance() and step_back()."""

import datetime
from unittest.mock import MagicMock

import pandas as pd

from brms.core.events import DateAdvanced, DateReverted, EventBus
from brms.core.metrics.base import MetricRegistry
from brms.core.models.accounting.rules.base import RuleRegistry
from brms.core.models.accounting.service import AccountingService
from brms.core.models.bank import Bank
from brms.core.models.market_data import MarketDataStore
from brms.core.services.data_service import BankingBook, TradingBook
from brms.core.services.metrics_service import MetricsService
from brms.core.services.simulation_service import LegacySimulationService, SimulationHistory


def _make_legacy_bank() -> Bank:
    """Create a Bank that also has legacy banking_book/trading_book attributes."""
    bb = BankingBook()
    tb = TradingBook()
    ledger = MagicMock()
    bank = MagicMock(spec=Bank)
    bank.name = "test"
    bank.banking_book = bb
    bank.trading_book = tb
    bank.ledger = ledger
    return bank


def _make_service() -> LegacySimulationService:
    bank = _make_legacy_bank()

    store = MarketDataStore()
    yields = pd.DataFrame(
        {"1Y": [0.03, 0.035, 0.04]},
        index=pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"]),
    )
    yields.index.name = "date"
    store.add_frame("yields", yields)

    rule_registry = RuleRegistry()
    acct_service = AccountingService()
    metric_registry = MetricRegistry()
    metrics_service = MetricsService(metric_registry)
    history = SimulationHistory()
    event_bus = EventBus()

    return LegacySimulationService(
        bank=bank,
        market_data=store,
        rule_registry=rule_registry,
        accounting_service=acct_service,
        metrics_service=metrics_service,
        history=history,
        event_bus=event_bus,
    )


def test_advance_moves_to_next_date() -> None:  # noqa: D103
    service = _make_service()
    service.advance()
    assert service.current_date == datetime.date(2024, 1, 1)  # noqa: S101


def test_advance_twice() -> None:  # noqa: D103
    service = _make_service()
    service.advance()
    service.advance()
    assert service.current_date == datetime.date(2024, 1, 2)  # noqa: S101


def test_advance_emits_event() -> None:  # noqa: D103
    service = _make_service()
    received = []
    service._events.subscribe(DateAdvanced, lambda e: received.append(e))  # noqa: SLF001
    service.advance()
    assert len(received) == 1  # noqa: S101
    assert received[0].date == datetime.date(2024, 1, 1)  # noqa: S101


def test_advance_pushes_day_record() -> None:  # noqa: D103
    service = _make_service()
    service.advance()
    assert len(service.history.dates) == 1  # noqa: S101


def test_step_back_reverses() -> None:  # noqa: D103
    service = _make_service()
    service.advance()
    received = []
    service._events.subscribe(DateReverted, lambda e: received.append(e))  # noqa: SLF001
    service.step_back()
    assert len(service.history.dates) == 0  # noqa: S101
    assert service.current_date is None  # noqa: S101
    assert len(received) == 1  # noqa: S101


def test_advance_twice_step_back() -> None:  # noqa: D103
    service = _make_service()
    service.advance()
    service.advance()
    assert service.current_date == datetime.date(2024, 1, 2)  # noqa: S101
    service.step_back()
    assert service.current_date == datetime.date(2024, 1, 1)  # noqa: S101


def test_step_back_emits_instrument_events() -> None:
    """step_back() emits InstrumentAdded when reversing a 'removed' change."""
    from brms.core.events import InstrumentAdded
    from brms.core.services.simulation_service import InstrumentChange

    service = _make_service()
    service.advance()

    # Manually inject an instrument change
    day = service.history.current_day
    mock_inst = MagicMock()
    mock_inst.id = "test-bond"
    day.instrument_changes.append(
        InstrumentChange(instrument=mock_inst, book_type="banking", action="removed"),
    )

    added_events: list[InstrumentAdded] = []
    service._events.subscribe(InstrumentAdded, lambda e: added_events.append(e))  # noqa: SLF001
    service.step_back()

    assert len(added_events) == 1  # noqa: S101
    assert added_events[0].instrument_id == "test-bond"  # noqa: S101
