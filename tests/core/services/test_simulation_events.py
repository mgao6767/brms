"""Tests that SimulationService.advance() emits granular events."""
# ruff: noqa: S101

import datetime
from unittest.mock import MagicMock

from brms.core.events import (
    DateAdvanced,
    EventBus,
    MetricsComputed,
    StatementsChanged,
    TransactionsRecorded,
    ValuationsUpdated,
)
from brms.core.services.simulation_service import SimulationService


def _make_simulation_service() -> tuple[SimulationService, EventBus, list]:
    event_bus = EventBus()
    received: list[object] = []

    event_bus.subscribe(ValuationsUpdated, lambda e: received.append(e))
    event_bus.subscribe(TransactionsRecorded, lambda e: received.append(e))
    event_bus.subscribe(StatementsChanged, lambda e: received.append(e))
    event_bus.subscribe(MetricsComputed, lambda e: received.append(e))
    event_bus.subscribe(DateAdvanced, lambda e: received.append(e))

    bank = MagicMock()
    bank.positions.open_positions.return_value = []
    market_data = MagicMock()
    market_data.available_dates.return_value = [datetime.date(2024, 1, 1), datetime.date(2024, 1, 2)]
    market_data.has_data.return_value = True
    market_data.get_state_or_none.return_value = MagicMock()

    valuation_store = MagicMock()
    valuation_store.snapshot.return_value = {}
    metric_store = MagicMock()
    metric_store.get.return_value = None

    ss = SimulationService(
        bank=bank,
        market_data=market_data,
        valuation_service=MagicMock(),
        rule_engine=MagicMock(apply=MagicMock(return_value=[])),
        accounting_service=MagicMock(),
        metrics_service=MagicMock(),
        valuation_store=valuation_store,
        metric_store=metric_store,
        transaction_log=MagicMock(),
        event_bus=event_bus,
    )
    return ss, event_bus, received


def test_advance_emits_all_events_in_order() -> None:
    ss, _, received = _make_simulation_service()
    ss.advance(datetime.date(2024, 1, 1))
    event_types = [type(e) for e in received]
    assert event_types == [
        ValuationsUpdated,
        TransactionsRecorded,
        StatementsChanged,
        MetricsComputed,
        DateAdvanced,
    ]


def test_advance_valuations_event_carries_date() -> None:
    ss, _, received = _make_simulation_service()
    ss.advance(datetime.date(2024, 1, 1))
    val_event = received[0]
    assert isinstance(val_event, ValuationsUpdated)
    assert val_event.date == datetime.date(2024, 1, 1)


def test_advance_transactions_event_carries_transactions() -> None:
    ss, _, received = _make_simulation_service()
    ss.advance(datetime.date(2024, 1, 1))
    tx_event = received[1]
    assert isinstance(tx_event, TransactionsRecorded)
    assert isinstance(tx_event.transactions, tuple)
