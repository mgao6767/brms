"""Integration test: end-to-end v2 core pipeline (Bank, stores, SimulationService)."""

from __future__ import annotations

import datetime
from decimal import Decimal

import pandas as pd

from brms.core.enums import BookType, MeasurementBasis, PositionSide, ValuationType
from brms.core.events import DateAdvanced, EventBus
from brms.core.metrics.base import MetricRegistry
from brms.core.models.accounting.bank_accounts import BankChartOfAccounts
from brms.core.models.accounting.journal import Journal
from brms.core.models.accounting.ledger import Ledger
from brms.core.services.accounting_service import AccountingService
from brms.core.models.bank import Bank
from brms.core.models.instruments.deposits import Cash
from brms.core.models.market_data import MarketDataStore
from brms.core.models.position import Position
from brms.core.services.metrics_service import MetricsService
from brms.core.services.rule_engine import RuleEngine
from brms.core.services.simulation_service import SimulationService
from brms.core.services.valuation_service import ValuationService
from brms.core.services.valuation_strategies import CarryingValueStrategy
from brms.core.stores.instrument_store import InstrumentStore
from brms.core.stores.metric_store import MetricStore
from brms.core.stores.position_store import PositionStore
from brms.core.stores.transaction_log import TransactionLog
from brms.core.stores.valuation_store import ValuationStore


def test_full_v2_flow() -> None:
    """End-to-end v2: create bank, advance 3 days, check stores."""
    # Setup bank
    coa = BankChartOfAccounts()
    ledger = Ledger(chart_of_accounts=coa, journal=Journal())
    bank = Bank(name="V2 Test", instruments=InstrumentStore(), positions=PositionStore(), ledger=ledger)

    # Add a cash instrument + position directly (no zip in this test)
    cash = Cash()
    cash.id = "cash-1"
    cash.face_value = Decimal("5000000")  # type: ignore[attr-defined]
    bank.instruments.add(cash)

    pos = Position(
        id="pos-1",
        instrument_id="cash-1",
        book_type=BookType.BANKING,
        measurement_basis=MeasurementBasis.AMORTIZED_COST,
        side=PositionSide.LONG,
        acquisition_date=datetime.date(2024, 1, 1),
        acquisition_cost=Decimal("5000000"),
    )
    bank.positions.add(pos)

    # Market data
    store = MarketDataStore()
    yields = pd.DataFrame(
        {"1 Yr": [0.04, 0.041, 0.042]},
        index=pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"]),
    )
    yields.index.name = "date"
    store.add_frame("yields", yields)

    # Services
    vs = ValuationService()
    vs.register_strategy(MeasurementBasis.AMORTIZED_COST, CarryingValueStrategy())
    event_bus = EventBus()
    events: list[DateAdvanced] = []
    event_bus.subscribe(DateAdvanced, lambda e: events.append(e))

    valuation_store = ValuationStore()
    metric_store = MetricStore()
    transaction_log = TransactionLog()

    sim = SimulationService(
        bank=bank,
        market_data=store,
        valuation_service=vs,
        rule_engine=RuleEngine(),
        accounting_service=AccountingService(),
        metrics_service=MetricsService(MetricRegistry()),
        valuation_store=valuation_store,
        metric_store=metric_store,
        transaction_log=transaction_log,
        event_bus=event_bus,
    )

    # Advance 3 days
    sim.advance(datetime.date(2024, 1, 1))
    sim.advance(datetime.date(2024, 1, 2))
    sim.advance(datetime.date(2024, 1, 3))

    # Verify events emitted
    assert len(events) == 3  # noqa: PLR2004, S101

    # Verify ValuationStore has data for day 1
    val = valuation_store.get("pos-1", datetime.date(2024, 1, 1), ValuationType.CARRYING_VALUE)
    assert val is not None  # noqa: S101
    assert val == Decimal("5000000")  # noqa: S101

    # Verify ValuationStore has data for all 3 days
    series = valuation_store.series("pos-1", ValuationType.CARRYING_VALUE)
    assert len(series) == 3  # noqa: PLR2004, S101

    # Verify positions still open
    assert len(bank.positions.open_positions()) == 1  # noqa: S101
