"""Tests for SimulationService: advance() and step_back()."""

import datetime
from unittest.mock import MagicMock

import pandas as pd

from brms.core.events import DateAdvanced, DateReverted, EventBus
from brms.core.metrics.base import MetricRegistry
from brms.core.models.accounting.rules.base import RuleRegistry
from brms.core.models.accounting.service import AccountingService
from brms.core.models.bank import Bank
from brms.core.models.books import BankingBook, TradingBook
from brms.core.models.history import SimulationHistory
from brms.core.models.market_data import MarketDataStore
from brms.core.services.metrics_service import MetricsService
from brms.core.services.simulation_service import SimulationService


def _make_service() -> SimulationService:
    bb = BankingBook()
    tb = TradingBook()
    ledger = MagicMock()
    bank = Bank("test", bb, tb, ledger)

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

    return SimulationService(
        bank=bank,
        market_data=store,
        rule_registry=rule_registry,
        accounting_service=acct_service,
        metrics_service=metrics_service,
        history=history,
        event_bus=event_bus,
    )


def test_advance_moves_to_next_date() -> None:
    service = _make_service()
    service.advance()
    assert service.current_date == datetime.date(2024, 1, 1)


def test_advance_twice() -> None:
    service = _make_service()
    service.advance()
    service.advance()
    assert service.current_date == datetime.date(2024, 1, 2)


def test_advance_emits_event() -> None:
    service = _make_service()
    received = []
    service._events.subscribe(DateAdvanced, lambda e: received.append(e))
    service.advance()
    assert len(received) == 1
    assert received[0].date == datetime.date(2024, 1, 1)


def test_advance_pushes_day_record() -> None:
    service = _make_service()
    service.advance()
    assert len(service.history.dates) == 1


def test_step_back_reverses() -> None:
    service = _make_service()
    service.advance()
    received = []
    service._events.subscribe(DateReverted, lambda e: received.append(e))
    service.step_back()
    assert len(service.history.dates) == 0
    assert service.current_date is None
    assert len(received) == 1


def test_advance_twice_step_back() -> None:
    service = _make_service()
    service.advance()
    service.advance()
    assert service.current_date == datetime.date(2024, 1, 2)
    service.step_back()
    assert service.current_date == datetime.date(2024, 1, 1)
