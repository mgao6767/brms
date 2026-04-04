"""Main module for the BRMS application."""

import sys

from PySide6.QtWidgets import QApplication

from brms import DEBUG_MODE
from brms.controllers.main_controller import MainController
from brms.core.events import EventBus
from brms.core.metrics.base import MetricRegistry
from brms.core.models.accounting.rules.base import RuleRegistry
from brms.core.models.accounting.service import AccountingService
from brms.core.models.history import SimulationHistory
from brms.core.services.metrics_service import MetricsService
from brms.core.services.risk_service import RiskService
from brms.core.services.valuation_service import ValuationService
from brms.models.simulation import Simulation as SimulationModel
from brms.views.main_window import MainWindow


def _build_core_services() -> dict:
    """Instantiate and wire core domain services.

    Returns a dict of named services that can be passed to controllers.
    """
    event_bus = EventBus()
    rule_registry = RuleRegistry()
    metric_registry = MetricRegistry()
    accounting_service = AccountingService()
    metrics_service = MetricsService(metric_registry)
    valuation_service = ValuationService()
    risk_service = RiskService()
    history = SimulationHistory()

    return {
        "event_bus": event_bus,
        "rule_registry": rule_registry,
        "metric_registry": metric_registry,
        "accounting_service": accounting_service,
        "metrics_service": metrics_service,
        "valuation_service": valuation_service,
        "risk_service": risk_service,
        "history": history,
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

        # Legacy simulation model (still used by controllers and views)
        self.model = SimulationModel()

        self.view = MainWindow()
        self.controller = MainController(
            self.model,
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
