"""Main module for the BRMS application."""

import sys
from pathlib import Path

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


def _build_core_services() -> dict:
    """Instantiate and wire all core services."""
    event_bus = EventBus()
    instrument_registry = default_instrument_registry()
    rule_engine = RuleEngine(default_rules())
    metric_registry = MetricRegistry(default_metrics())
    valuation_service = ValuationService(default_valuation_strategies())

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

    default_zip = Path(__file__).parent / "data" / "default_simulation.zip"
    default_zip = Path("temp/simple_bank.zip")
    if default_zip.exists():
        loader = ZipLoader(path=default_zip, instrument_registry=instrument_registry)
        data_service.load_and_initialize(loader, simulation_service)

    return {
        "event_bus": event_bus,
        "instrument_registry": instrument_registry,
        "data_service": data_service,
        "rule_engine": rule_engine,
        "metric_registry": metric_registry,
        "accounting_service": accounting_service,
        "metrics_service": metrics_service,
        "valuation_service": valuation_service,
        "reporting_service": reporting_service,
        "risk_service": risk_service,
        "valuation_store": valuation_store,
        "metric_store": metric_store,
        "transaction_log": transaction_log,
        "simulation_service": simulation_service,
    }


def main() -> None:
    """Run the main entry point for the BRMS application."""
    from brms.app.application import App

    core_services = _build_core_services()
    app = App(sys.argv, core_services)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
