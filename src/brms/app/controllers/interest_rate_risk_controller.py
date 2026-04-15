"""Controller for the Interest Rate Risk tab."""

from __future__ import annotations

from typing import TYPE_CHECKING

from brms.app.controllers.base import BRMSController
from brms.core.events import DateAdvanced
from brms.core.metrics.risk.interest_rate_risk.maturity_gap import MaturityGapModel

if TYPE_CHECKING:
    from brms.app.views.interest_rate_risk import BRMSInterestRateRiskWidget
    from brms.core.events import EventBus
    from brms.core.models.bank import Bank
    from brms.core.stores.valuation_store import ValuationStore


class InterestRateRiskController(BRMSController):
    """Subscribes to DateAdvanced and recomputes the maturity gap model."""

    def __init__(
        self,
        view: BRMSInterestRateRiskWidget,
        event_bus: EventBus,
        bank: Bank,
        valuation_store: ValuationStore,
    ) -> None:
        """Initialize the controller."""
        super().__init__()
        self.view = view
        self._bank = bank
        self._valuation_store = valuation_store
        self._model = MaturityGapModel()
        self._dirty = False
        event_bus.subscribe(DateAdvanced, self._on_date_advanced)

    def _on_date_advanced(self, event: DateAdvanced) -> None:
        """Recompute maturity gap on each date advance."""
        if self.view.isVisible():
            result = self._model.compute(self._bank, event.date, self._valuation_store)
            self.view.update(result)
        else:
            self._dirty = True
            self._last_date = event.date

    def on_visible(self) -> None:
        """Flush deferred computation when the tab becomes visible."""
        if self._dirty and hasattr(self, "_last_date"):
            result = self._model.compute(self._bank, self._last_date, self._valuation_store)
            self.view.update(result)
            self._dirty = False

    def init(self, date: object) -> None:
        """Compute initial gap on load."""
        if date is not None:
            result = self._model.compute(self._bank, date, self._valuation_store)
            self.view.update(result)
