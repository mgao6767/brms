"""Main module for the BRMS application."""

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from brms import DEBUG_MODE
from brms.app.controllers.main_controller import MainController
from brms.app.views.main_window import MainWindow
from brms.core.enums import InstrumentClass
from brms.core.events import EventBus
from brms.core.metrics.base import MetricRegistry
from brms.core.metrics.capital import (
    TotalAssetsMetric,
    TotalEquityMetric,
    TotalLiabilitiesMetric,
)
from brms.core.models.accounting.bank_accounts import BankChartOfAccounts
from brms.core.models.accounting.journal import Journal
from brms.core.models.accounting.ledger import Ledger
from brms.core.models.bank import Bank
from brms.core.models.instruments.bonds import CoveredBond, FixedRateBond, TreasuryBond, TreasuryNote
from brms.core.models.instruments.deposits import Cash, Deposit
from brms.core.models.instruments.equity import CommonEquity
from brms.core.models.instruments.loans import (
    AmortizingFixedRateLoan,
    CommercialMortgage,
    CreditCard,
    Mortgage,
    PersonalLoan,
    ResidentialMortgage,
)
from brms.core.models.instruments.other import (
    Commitment,
    LetterOfCredit,
    RepurchaseAgreement,
    StandByLetterOfCredit,
    TradeLetterOfCredit,
)
from brms.core.models.instruments.registry import InstrumentRegistry
from brms.core.models.market_data import MarketDataStore
from brms.core.rules.amortization import AmortizationRule
from brms.core.rules.coupon import CouponPaymentRule
from brms.core.rules.deposit_interest import DepositInterestAccrualRule, DepositInterestSettlementRule
from brms.core.rules.interest_accrual import InterestIncomeAccrualRule
from brms.core.rules.mark_to_market import MarkToMarketRule
from brms.core.rules.maturity import MaturityRule
from brms.core.services.accounting_service import AccountingService
from brms.core.services.data_service import DataService
from brms.core.services.loaders import ZipLoader
from brms.core.services.metrics_service import MetricsService
from brms.core.services.reporting_service import ReportingService
from brms.core.services.risk_service import RiskService
from brms.core.services.rule_engine import RuleEngine
from brms.core.services.simulation_service import SimulationService
from brms.core.services.valuation_service import ValuationService
from brms.core.services.valuation_strategies import (
    AmortizedCostStrategy,
    FairValueStrategy,
    OutstandingBalanceStrategy,
)
from brms.core.stores.instrument_store import InstrumentStore
from brms.core.stores.metric_store import MetricStore
from brms.core.stores.position_store import PositionStore
from brms.core.stores.transaction_log import TransactionLog
from brms.core.stores.valuation_store import ValuationStore


def _build_instrument_registry() -> InstrumentRegistry:
    """Create and populate an InstrumentRegistry with all known instrument types."""
    registry = InstrumentRegistry()
    registry.register("cash", Cash)
    registry.register("deposit", Deposit)
    registry.register("common_equity", CommonEquity)
    registry.register("fixed_rate_bond", FixedRateBond)
    registry.register("treasury_note", TreasuryNote)
    registry.register("treasury_bond", TreasuryBond)
    registry.register("covered_bond", CoveredBond)
    registry.register("amortizing_fixed_rate_loan", AmortizingFixedRateLoan)
    registry.register("mortgage", Mortgage)
    registry.register("residential_mortgage", ResidentialMortgage)
    registry.register("commercial_mortgage", CommercialMortgage)
    registry.register("personal_loan", PersonalLoan)
    registry.register("credit_card", CreditCard)
    registry.register("commitment", Commitment)
    registry.register("letter_of_credit", LetterOfCredit)
    registry.register("standby_letter_of_credit", StandByLetterOfCredit)
    registry.register("trade_letter_of_credit", TradeLetterOfCredit)
    registry.register("repurchase_agreement", RepurchaseAgreement)
    return registry


def _build_core_services() -> dict:
    """Instantiate and wire all v2 core services."""
    event_bus = EventBus()
    instrument_registry = _build_instrument_registry()

    # Rule engine
    rule_engine = RuleEngine()
    rule_engine.register(MaturityRule())
    rule_engine.register(CouponPaymentRule())
    rule_engine.register(MarkToMarketRule())
    rule_engine.register(AmortizationRule())
    rule_engine.register(DepositInterestAccrualRule())
    rule_engine.register(DepositInterestSettlementRule())
    rule_engine.register(InterestIncomeAccrualRule())

    # Metrics
    metric_registry = MetricRegistry()
    metric_registry.register(TotalAssetsMetric())
    metric_registry.register(TotalLiabilitiesMetric())
    metric_registry.register(TotalEquityMetric())
    # CET1RatioMetric removed — requires proper CET1 capital and RWA calculations

    # Valuation service with strategies
    valuation_service = ValuationService()
    valuation_service.register_strategy(InstrumentClass.HTM, AmortizedCostStrategy())
    valuation_service.register_strategy(InstrumentClass.FVOCI, FairValueStrategy())
    valuation_service.register_strategy(InstrumentClass.FVTPL, FairValueStrategy())
    valuation_service.register_strategy(InstrumentClass.LOAN_AND_MORTGAGE, OutstandingBalanceStrategy())

    # Other services
    accounting_service = AccountingService()
    metrics_service = MetricsService(metric_registry)
    reporting_service = ReportingService()
    risk_service = RiskService()
    data_service = DataService()

    # Stores
    valuation_store = ValuationStore()
    metric_store = MetricStore()
    transaction_log = TransactionLog()

    # Bank with empty stores + ledger
    coa = BankChartOfAccounts()
    ledger = Ledger(chart_of_accounts=coa, journal=Journal())
    bank = Bank(
        name="BRMS Bank",
        instruments=InstrumentStore(),
        positions=PositionStore(),
        ledger=ledger,
    )

    # Market data store (populated by DataService)
    market_data = MarketDataStore()

    # Simulation service (v2 thin orchestrator)
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

    # Load default simulation zip and initialize (replay to start_date)
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


class App(QApplication):
    """BRMS application."""

    def __init__(self, sys_argv: list[str]) -> None:
        """Initialize the BRMS application."""
        super().__init__(sys_argv)
        font = self.font()
        font.setFamily("Monospace")
        self.setFont(font)

        self.core_services = _build_core_services()

        self.view = MainWindow()
        self.controller = MainController(
            self.view,
            core_services=self.core_services,
        )
        self.view.show()
        if DEBUG_MODE:
            self.view.debug_panel.show()


def main() -> None:
    """Run the main entry point for the BRMS application."""
    app = App(sys.argv)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
