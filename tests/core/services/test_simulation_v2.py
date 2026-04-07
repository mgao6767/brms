"""Tests for the V2 SimulationService thin orchestrator."""

import datetime
from unittest.mock import MagicMock

from brms.core.events import DateAdvanced, EventBus
from brms.core.services.simulation_service import SimulationService


def test_advance_calls_services_in_order() -> None:
    """advance() should call each collaborator in sequence and emit DateAdvanced."""
    bank = MagicMock()
    market_data = MagicMock()
    market_data.available_dates.return_value = [datetime.date(2024, 1, 1)]
    market_data.has_data.return_value = True
    market_data.get_state.return_value = MagicMock()
    market_data.get_state_or_none.return_value = MagicMock()
    valuation_service = MagicMock()
    rule_engine = MagicMock()
    rule_engine.apply.return_value = []
    accounting_service = MagicMock()
    metrics_service = MagicMock()
    valuation_store = MagicMock()
    metric_store = MagicMock()
    transaction_log = MagicMock()
    event_bus = EventBus()
    received = []
    event_bus.subscribe(DateAdvanced, lambda e: received.append(e))

    sim = SimulationService(
        bank=bank,
        market_data=market_data,
        valuation_service=valuation_service,
        rule_engine=rule_engine,
        accounting_service=accounting_service,
        metrics_service=metrics_service,
        valuation_store=valuation_store,
        metric_store=metric_store,
        transaction_log=transaction_log,
        event_bus=event_bus,
    )

    date = datetime.date(2024, 1, 1)
    sim.advance(date)

    valuation_service.value_all.assert_called_once()
    rule_engine.apply.assert_called_once()
    accounting_service.post_all.assert_called_once()
    transaction_log.record_batch.assert_called_once()
    metrics_service.compute.assert_called_once()
    assert len(received) == 1
    assert received[0].date == date
