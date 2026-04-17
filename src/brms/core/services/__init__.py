"""Core service layer for BRMS."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from brms.core.events import EventBus
    from brms.core.models.bank import Bank
    from brms.core.models.market_data import MarketDataStore
    from brms.core.services.accounting_service import AccountingService
    from brms.core.services.data_service import DataService
    from brms.core.services.reporting_service import ReportingService
    from brms.core.services.risk_service import RiskService
    from brms.core.services.simulation_service import SimulationService
    from brms.core.stores.metric_store import MetricStore
    from brms.core.stores.transaction_log import TransactionLog
    from brms.core.stores.valuation_store import ValuationStore


@dataclass(frozen=True)
class CoreServices:
    """Typed container for all core-layer services, stores, and infrastructure."""

    event_bus: EventBus
    simulation_service: SimulationService
    bank: Bank
    market_data: MarketDataStore
    valuation_store: ValuationStore
    metric_store: MetricStore
    transaction_log: TransactionLog
    reporting_service: ReportingService
    risk_service: RiskService
    data_service: DataService
    accounting_service: AccountingService


def build_core_services(*, simulation_zip: Path | None = None) -> CoreServices:
    """Instantiate and wire all core services. Returns a frozen CoreServices."""
    import QuantLib as ql_  # noqa: N813

    from brms.core.events import EventBus
    from brms.core.metrics import default_metrics
    from brms.core.metrics.base import MetricRegistry
    from brms.core.models.accounting.bank_accounts import BankChartOfAccounts
    from brms.core.models.accounting.journal import Journal
    from brms.core.models.accounting.ledger import Ledger
    from brms.core.models.bank import Bank
    from brms.core.models.instruments import default_instrument_registry
    from brms.core.models.market_data import MarketDataStore
    from brms.core.rules import default_rules
    from brms.core.services.accounting_service import AccountingService
    from brms.core.services.benchmark_service import BenchmarkService
    from brms.core.services.data_service import DataService
    from brms.core.services.loaders import ZipLoader
    from brms.core.services.metrics_service import MetricsService
    from brms.core.services.reporting_service import ReportingService
    from brms.core.services.risk_service import RiskService
    from brms.core.services.rule_engine import RuleEngine
    from brms.core.services.simulation_service import SimulationService
    from brms.core.services.valuation_service import ValuationService
    from brms.core.services.valuation_strategies import default_valuation_strategies
    from brms.core.stores.instrument_store import InstrumentStore
    from brms.core.stores.metric_store import MetricStore
    from brms.core.stores.position_store import PositionStore
    from brms.core.stores.transaction_log import TransactionLog
    from brms.core.stores.valuation_store import ValuationStore

    event_bus = EventBus()
    instrument_registry = default_instrument_registry()

    shared_yield_handle = ql_.RelinkableYieldTermStructureHandle()
    benchmark_service = BenchmarkService(forwarding_handle=shared_yield_handle)

    from brms.core.models.instruments.loans import VariableRateLoan

    instrument_registry.register(
        "variable_rate_loan",
        lambda **kw: VariableRateLoan(ibor_index=benchmark_service.prime_index, **kw),
    )

    rule_engine = RuleEngine(default_rules())
    metric_registry = MetricRegistry(default_metrics())
    valuation_service = ValuationService(
        default_valuation_strategies(),
        benchmark_service=benchmark_service,
        yield_handle=shared_yield_handle,
    )

    accounting_service = AccountingService()
    metrics_service = MetricsService(metric_registry)
    reporting_service = ReportingService()
    risk_service = RiskService()
    data_service = DataService()

    valuation_store = ValuationStore()
    metric_store = MetricStore()
    transaction_log = TransactionLog()

    coa = BankChartOfAccounts()
    ledger = Ledger(chart_of_accounts=coa, journal=Journal())
    bank = Bank(
        name="BRMS Bank",
        instruments=InstrumentStore(),
        positions=PositionStore(),
        ledger=ledger,
    )

    market_data = MarketDataStore()

    simulation_service = SimulationService(
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

    if simulation_zip is None:
        import importlib.resources as pkg_resources

        simulation_zip = Path(str(pkg_resources.files("brms.data").joinpath("htm_treasury.zip")))
    if simulation_zip.exists():
        loader = ZipLoader(path=simulation_zip, instrument_registry=instrument_registry)
        data_service.load_and_initialize(loader, simulation_service)

    # Seed the valuation store so initial tree values match the BS
    if simulation_service.start_date is not None:
        import contextlib

        with contextlib.suppress(Exception):
            valuation_service.value_all(bank, market_data, simulation_service.start_date, valuation_store)

    return CoreServices(
        event_bus=event_bus,
        simulation_service=simulation_service,
        bank=bank,
        market_data=market_data,
        valuation_store=valuation_store,
        metric_store=metric_store,
        transaction_log=transaction_log,
        reporting_service=reporting_service,
        risk_service=risk_service,
        data_service=data_service,
        accounting_service=accounting_service,
    )
