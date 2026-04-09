"""Controller for financial statement views — subscribes to StatementsChanged."""

from __future__ import annotations

from typing import TYPE_CHECKING

from brms.app.controllers.base import BRMSController
from brms.app.reporting import HTMLStatementRenderer
from brms.core.events import StatementsChanged

if TYPE_CHECKING:
    from brms.app.views.statement_viewer.statement_viewer_widget import BRMSStatementViewer
    from brms.core.events import EventBus
    from brms.core.models.accounting.ledger import Ledger
    from brms.core.services.reporting_service import ReportingService


class StatementController(BRMSController):
    """Subscribes to StatementsChanged, renders HTML statements."""

    def __init__(
        self,
        view: BRMSStatementViewer,
        event_bus: EventBus,
        reporting_service: ReportingService,
        ledger: Ledger,
    ) -> None:
        """Initialize the statement controller."""
        super().__init__()
        self.view = view
        self._reporting = reporting_service
        self._ledger = ledger
        self._renderer = HTMLStatementRenderer()
        self._dirty = False
        self._last_date: object = None
        event_bus.subscribe(StatementsChanged, self._on_statements_changed)

    def refresh(self, date: object = None) -> None:
        """Manually trigger a statement refresh."""
        self._render(date)

    def on_visible(self) -> None:
        """Flush deferred statement render when the viewer becomes visible."""
        if self._dirty:
            self._render(self._last_date)
            self._dirty = False

    def _on_statements_changed(self, event: StatementsChanged) -> None:
        self._last_date = event.date
        if self.view.isVisible():
            self._render(event.date)
        else:
            self._dirty = True

    def _render(self, date: object = None) -> None:
        tb_data = self._reporting.trial_balance(self._ledger)
        bs_data = self._reporting.balance_sheet(self._ledger, date=date)
        is_data = self._reporting.income_statement(self._ledger)

        tb_html = self._renderer.render_trial_balance(tb_data, date)
        bs_html = self._renderer.render_balance_sheet(bs_data, date)
        is_html = self._renderer.render_income_statement(is_data, date)

        # Save scroll positions
        tb_v = self.view.trial_balance_browser.verticalScrollBar().value()
        tb_h = self.view.trial_balance_browser.horizontalScrollBar().value()
        is_v = self.view.income_statement_browser.verticalScrollBar().value()
        is_h = self.view.income_statement_browser.horizontalScrollBar().value()
        bs_v = self.view.balance_sheet_browser.verticalScrollBar().value()
        bs_h = self.view.balance_sheet_browser.horizontalScrollBar().value()

        self.view.trial_balance_browser.setHtml(tb_html)
        self.view.income_statement_browser.setHtml(is_html)
        self.view.balance_sheet_browser.setHtml(bs_html)

        self.view.trial_balance_browser.verticalScrollBar().setValue(tb_v)
        self.view.trial_balance_browser.horizontalScrollBar().setValue(tb_h)
        self.view.income_statement_browser.verticalScrollBar().setValue(is_v)
        self.view.income_statement_browser.horizontalScrollBar().setValue(is_h)
        self.view.balance_sheet_browser.verticalScrollBar().setValue(bs_v)
        self.view.balance_sheet_browser.horizontalScrollBar().setValue(bs_h)
