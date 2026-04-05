"""Controller for managing bank operations via core services and EventBus."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Signal

from brms.app.controllers.bank_book_controller import BankingBookController, TradingBookController
from brms.app.controllers.base import BRMSController
from brms.app.reporting import HTMLStatementRenderer
from brms.core.events import InstrumentAdded, InstrumentRemoved
from brms.core.models.books import Position

if TYPE_CHECKING:
    from brms.app.controllers.inspector_controller import InspectorController
    from brms.app.views.bank_book_widget import BRMSBankingBookWidget, BRMSTradingBookWidget
    from brms.app.views.statement_viewer_widget import BRMSStatementViewer
    from brms.core.events import EventBus
    from brms.core.models.bank import Bank
    from brms.core.services.reporting_service import ReportingService


class BankController(BRMSController):
    """Controller for managing bank operations using core services and EventBus.

    Uses ReportingService for financial statements and subscribes to instrument
    lifecycle events via the EventBus.
    """

    bank_financials_updated = Signal(dict, name="Bank Financials Updated")

    def __init__(  # noqa: PLR0913
        self,
        bank: Bank,
        event_bus: EventBus,
        reporting_service: ReportingService,
        banking_book_view: BRMSBankingBookWidget,
        trading_book_view: BRMSTradingBookWidget,
        inspector_ctrl: InspectorController,
        statement_view: BRMSStatementViewer,
    ) -> None:
        """Initialize the BankController with core services."""
        super().__init__()
        self.bank = bank
        self._event_bus = event_bus
        self._reporting = reporting_service
        self._renderer = HTMLStatementRenderer()
        self.statement_view = statement_view
        self.inspector_ctrl = inspector_ctrl

        # Sub controllers
        self.banking_book_ctrl = BankingBookController(bank.banking_book, banking_book_view, inspector_ctrl)
        self.trading_book_ctrl = TradingBookController(bank.trading_book, trading_book_view, inspector_ctrl)

        # Subscribe to instrument lifecycle events
        event_bus.subscribe(InstrumentAdded, self._on_instrument_added)
        event_bus.subscribe(InstrumentRemoved, self._on_instrument_removed)

    def _on_instrument_added(self, event: InstrumentAdded) -> None:
        """Handle an instrument being added to a book."""
        position = Position.LONG  # Default; P4-7 will refine position handling
        if event.book_type == "banking":
            self.banking_book_ctrl.add_instrument(event.instrument, position)
        else:
            self.trading_book_ctrl.add_instrument(event.instrument, position)

    def _on_instrument_removed(self, event: InstrumentRemoved) -> None:
        """Handle an instrument being removed from a book."""
        position = Position.LONG  # Default; P4-7 will refine position handling
        if event.book_type == "banking":
            self.banking_book_ctrl.remove_instrument(event.instrument, position)
        else:
            self.trading_book_ctrl.remove_instrument(event.instrument, position)

    def update_statement(self, date=None) -> None:  # noqa: ANN001
        """Refresh financial statement views using ReportingService and HTMLStatementRenderer."""
        tb_data = self._reporting.trial_balance(self.bank.ledger)
        bs_data = self._reporting.balance_sheet(self.bank.ledger)
        is_data = self._reporting.income_statement(self.bank.ledger)

        tb_html = self._renderer.render_trial_balance(tb_data, date)
        bs_html = self._renderer.render_balance_sheet(bs_data, date)
        is_html = self._renderer.render_income_statement(is_data, date)

        # Save current scroll positions
        tb_v = self.statement_view.trial_balance_browser.verticalScrollBar().value()
        tb_h = self.statement_view.trial_balance_browser.horizontalScrollBar().value()
        is_v = self.statement_view.income_statement_browser.verticalScrollBar().value()
        is_h = self.statement_view.income_statement_browser.horizontalScrollBar().value()
        bs_v = self.statement_view.balance_sheet_browser.verticalScrollBar().value()
        bs_h = self.statement_view.balance_sheet_browser.horizontalScrollBar().value()

        # Set new HTML content
        self.statement_view.trial_balance_browser.setHtml(tb_html)
        self.statement_view.income_statement_browser.setHtml(is_html)
        self.statement_view.balance_sheet_browser.setHtml(bs_html)

        # Restore scroll positions
        self.statement_view.trial_balance_browser.verticalScrollBar().setValue(tb_v)
        self.statement_view.trial_balance_browser.horizontalScrollBar().setValue(tb_h)
        self.statement_view.income_statement_browser.verticalScrollBar().setValue(is_v)
        self.statement_view.income_statement_browser.horizontalScrollBar().setValue(is_h)
        self.statement_view.balance_sheet_browser.verticalScrollBar().setValue(bs_v)
        self.statement_view.balance_sheet_browser.horizontalScrollBar().setValue(bs_h)

        # Emit balance-sheet data so dashboard can update
        if date is not None:
            self.bank_financials_updated.emit(bs_data)
