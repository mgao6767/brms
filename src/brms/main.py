"""Main module for the BRMS application."""

import sys
from pathlib import Path

import pandas as pd
from PySide6.QtWidgets import QApplication

from brms import DEBUG_MODE
from brms.app.controllers.main_controller import MainController
from brms.app.views.main_window import MainWindow
from brms.core.events import EventBus
from brms.core.metrics.base import MetricRegistry
from brms.core.metrics.capital import (
    CET1RatioMetric,
    TotalAssetsMetric,
    TotalEquityMetric,
    TotalLiabilitiesMetric,
)
from brms.core.models.accounting.accounts import BankChartOfAccounts
from brms.core.models.accounting.ledger import Ledger
from brms.core.models.accounting.rules.amortization import AmortizationRule
from brms.core.models.accounting.rules.base import RuleRegistry
from brms.core.models.accounting.rules.coupon import CouponPaymentRule
from brms.core.models.accounting.rules.interest import InterestPaymentRule
from brms.core.models.accounting.rules.mark_to_market import MarkToMarketRule
from brms.core.models.accounting.rules.maturity import MaturityRule
from brms.core.models.accounting.service import AccountingService
from brms.core.models.bank import Bank
from brms.core.models.books import BankingBook, TradingBook
from brms.core.models.history import SimulationHistory
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
from brms.core.services.data_service import DataService
from brms.core.services.metrics_service import MetricsService
from brms.core.services.reporting_service import ReportingService
from brms.core.services.risk_service import RiskService
from brms.core.services.simulation_service import SimulationService
from brms.core.services.valuation_service import ValuationService
from brms.data import DEFAULT_DATA_FOLDER


def _build_instrument_registry() -> InstrumentRegistry:
    """Create and populate an InstrumentRegistry with all known instrument types."""
    registry = InstrumentRegistry()
    # Deposits
    registry.register("cash", Cash)
    registry.register("deposit", Deposit)
    # Equity
    registry.register("common_equity", CommonEquity)
    # Bonds
    registry.register("fixed_rate_bond", FixedRateBond)
    registry.register("treasury_note", TreasuryNote)
    registry.register("treasury_bond", TreasuryBond)
    registry.register("covered_bond", CoveredBond)
    # Loans
    registry.register("amortizing_fixed_rate_loan", AmortizingFixedRateLoan)
    registry.register("mortgage", Mortgage)
    registry.register("residential_mortgage", ResidentialMortgage)
    registry.register("commercial_mortgage", CommercialMortgage)
    registry.register("personal_loan", PersonalLoan)
    registry.register("credit_card", CreditCard)
    # Off-balance-sheet / other
    registry.register("commitment", Commitment)
    registry.register("letter_of_credit", LetterOfCredit)
    registry.register("standby_letter_of_credit", StandByLetterOfCredit)
    registry.register("trade_letter_of_credit", TradeLetterOfCredit)
    registry.register("repurchase_agreement", RepurchaseAgreement)
    return registry


def _load_market_data() -> MarketDataStore:
    """Load market data from the default CSV files into a MarketDataStore."""
    store = MarketDataStore()
    yields_path = Path(DEFAULT_DATA_FOLDER) / "treasury_yields.csv"
    yields_frame = pd.read_csv(yields_path, parse_dates=["date"], index_col="date")
    store.add_frame("yields", yields_frame)
    return store


def _build_core_services() -> dict:
    """Instantiate and wire core domain services.

    Returns a dict of named services that can be passed to controllers.
    """
    event_bus = EventBus()
    instrument_registry = _build_instrument_registry()
    data_service = DataService(instrument_registry=instrument_registry)
    rule_registry = RuleRegistry()
    rule_registry.register(MaturityRule())
    rule_registry.register(CouponPaymentRule())
    rule_registry.register(InterestPaymentRule())
    rule_registry.register(MarkToMarketRule())
    rule_registry.register(AmortizationRule())
    metric_registry = MetricRegistry()
    metric_registry.register(TotalAssetsMetric())
    metric_registry.register(TotalLiabilitiesMetric())
    metric_registry.register(TotalEquityMetric())
    metric_registry.register(CET1RatioMetric())
    accounting_service = AccountingService()
    metrics_service = MetricsService(metric_registry)
    valuation_service = ValuationService()
    reporting_service = ReportingService()
    risk_service = RiskService()
    history = SimulationHistory()

    # Build core Bank with BankChartOfAccounts-backed Ledger
    coa = BankChartOfAccounts()
    ledger = Ledger(chart_of_accounts=coa)
    banking_book = BankingBook()
    trading_book = TradingBook()
    core_bank = Bank(name="Core Bank", banking_book=banking_book, trading_book=trading_book, ledger=ledger)

    # Build MarketDataStore from CSV yield data
    market_data = _load_market_data()

    # Create SimulationService with all wired services
    simulation_service = SimulationService(
        bank=core_bank,
        market_data=market_data,
        rule_registry=rule_registry,
        accounting_service=accounting_service,
        metrics_service=metrics_service,
        history=history,
        event_bus=event_bus,
    )

    return {
        "event_bus": event_bus,
        "instrument_registry": instrument_registry,
        "data_service": data_service,
        "rule_registry": rule_registry,
        "metric_registry": metric_registry,
        "accounting_service": accounting_service,
        "metrics_service": metrics_service,
        "valuation_service": valuation_service,
        "reporting_service": reporting_service,
        "risk_service": risk_service,
        "history": history,
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

        # Core domain services (new architecture)
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
