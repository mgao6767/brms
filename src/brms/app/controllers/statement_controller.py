"""Controller for financial statement views — subscribes to StatementsChanged."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtWidgets import QFileDialog

from brms.app.controllers.base import BRMSController
from brms.app.reporting import HTMLStatementRenderer
from brms.core.events import StatementsChanged

if TYPE_CHECKING:
    import datetime

    from brms.app.views.statement_viewer.statement_viewer_widget import BRMSStatementViewer
    from brms.core.events import EventBus
    from brms.core.models.accounting.ledger import Ledger
    from brms.core.services.reporting_service import ReportingService


class StatementController(BRMSController):
    """Subscribes to StatementsChanged, populates statement tree models."""

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
        self._last_date: datetime.date | None = None
        event_bus.subscribe(StatementsChanged, self._on_statements_changed)

        # Connect export actions
        self.view.trial_balance_tab.export_action.triggered.connect(
            lambda: self._on_export("trial_balance"),
        )
        self.view.income_statement_tab.export_action.triggered.connect(
            lambda: self._on_export("income_statement"),
        )
        self.view.balance_sheet_tab.export_action.triggered.connect(
            lambda: self._on_export("balance_sheet"),
        )

    def reset(self) -> None:
        """Clear all statement models."""
        self.view.trial_balance_model._reset()  # noqa: SLF001
        self.view.income_statement_model._reset()  # noqa: SLF001
        self.view.balance_sheet_model._reset()  # noqa: SLF001
        self._dirty = False
        self._last_date = None

    def refresh(self, date: datetime.date | None = None) -> None:
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

    def _render(self, date: datetime.date | None = None) -> None:
        # Trial balance — flat, uses ReportingService output
        tb_data = self._reporting.trial_balance(self._ledger)
        self.view.trial_balance_model.update(tb_data)

        # Balance sheet — walk closed ledger's chart of accounts
        closed = copy.deepcopy(self._ledger)
        if date is not None:
            closed.close_ledger(date)
        self.view.balance_sheet_model.update(closed.chart_of_accounts)

        # Income statement — walk unclosed ledger's chart of accounts
        self.view.income_statement_model.update(self._ledger.chart_of_accounts)

        # Expand all trees so accounts are visible
        self.view.trial_balance_tab.tree.expandAll()
        self.view.income_statement_tab.tree.expandAll()
        self.view.balance_sheet_tab.tree.expandAll()

    def _on_export(self, statement_type: str) -> None:
        """Export a statement as HTML via file dialog."""
        date = self._last_date

        if statement_type == "trial_balance":
            data = self._reporting.trial_balance(self._ledger)
            html = self._renderer.render_trial_balance(data, date)
            title = "Trial Balance"
        elif statement_type == "balance_sheet":
            data = self._reporting.balance_sheet(self._ledger, date)
            html = self._renderer.render_balance_sheet(data, date)
            title = "Balance Sheet"
        elif statement_type == "income_statement":
            data = self._reporting.income_statement(self._ledger)
            html = self._renderer.render_income_statement(data, date)
            title = "Income Statement"
        else:
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self.view,
            caption=f"Export {title}",
            dir=f"BRMS - {title}",
            filter="HTML Files (*.html);;All Files (*)",
        )
        if file_path:
            Path(file_path).write_text(html, encoding="utf-8")
