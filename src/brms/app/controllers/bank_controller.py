"""Controller for managing bank operations via core services and EventBus."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Signal

from brms.app.controllers.bank_book_controller import BankingBookController, TradingBookController
from brms.app.controllers.base import BRMSController
from brms.app.reporting import HTMLStatementRenderer
from brms.core.enums import PositionSide as Position
from brms.core.events import DateAdvanced, InstrumentAdded, InstrumentRemoved

if TYPE_CHECKING:
    from brms.app.controllers.inspector_controller import InspectorController
    from brms.app.views.bank_book_widget import BRMSBankingBookWidget, BRMSTradingBookWidget
    from brms.app.views.statement_viewer_widget import BRMSStatementViewer
    from brms.core.events import EventBus
    from brms.core.models.bank import Bank
    from brms.core.services.reporting_service import ReportingService
    from brms.core.stores.valuation_store import ValuationStore


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
        valuation_store: ValuationStore | None = None,
    ) -> None:
        """Initialize the BankController with core services."""
        super().__init__()
        self.bank = bank
        self._event_bus = event_bus
        self._reporting = reporting_service
        self._valuation_store = valuation_store
        self._renderer = HTMLStatementRenderer()
        self.statement_view = statement_view
        self.inspector_ctrl = inspector_ctrl

        # Sub controllers
        self.banking_book_ctrl = BankingBookController(bank.banking_book, banking_book_view, inspector_ctrl)
        self.trading_book_ctrl = TradingBookController(bank.trading_book, trading_book_view, inspector_ctrl)

        # Subscribe to events
        event_bus.subscribe(InstrumentAdded, self._on_instrument_added)
        event_bus.subscribe(InstrumentRemoved, self._on_instrument_removed)
        event_bus.subscribe(DateAdvanced, self._on_date_advanced)

        # Populate tree widgets with existing instruments
        self._populate_books()

    def _populate_books(self) -> None:
        """Populate the tree widgets with all existing instruments in the bank."""
        from brms.core.enums import BookType

        for pos in self.bank.positions.open_positions():
            try:
                instrument = self.bank.instruments.get(pos.instrument_id)
            except KeyError:
                continue
            side = Position.LONG if pos.side == Position.LONG else Position.SHORT
            ctrl = (
                self.banking_book_ctrl if pos.book_type == BookType.BANKING
                else self.trading_book_ctrl
            )
            ctrl.add_instrument(instrument, side, initial_value=float(pos.acquisition_cost))

    def _on_date_advanced(self, event: DateAdvanced) -> None:
        """Update instrument values in book trees from ValuationStore after each advance."""
        if self._valuation_store is None:
            return
        from brms.core.enums import BookType, ValuationType

        date = event.date
        for pos in self.bank.positions.open_positions():
            # Try fair value first, then carrying value
            val = self._valuation_store.get(pos.id, date, ValuationType.FAIR_VALUE)
            if val is None:
                val = self._valuation_store.get(pos.id, date, ValuationType.CARRYING_VALUE)
            if val is None:
                continue
            try:
                instrument = self.bank.instruments.get(pos.instrument_id)
            except KeyError:
                continue
            ctrl = (
                self.banking_book_ctrl if pos.book_type == BookType.BANKING
                else self.trading_book_ctrl
            )
            ctrl.update_instrument_value(instrument.id, float(val))

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

        # Add capital adequacy and liquidity metrics for the dashboard panel
        total_assets = bs_data.get("total_assets", 0.0)
        total_equity = bs_data.get("total_equity", 0.0)
        bs_data["cet1"] = total_equity  # simplified: CET1 = equity
        bs_data["cet1_ratio"] = total_equity / total_assets if total_assets else 0.0
        bs_data["tier1_capital_ratio"] = 0.0
        bs_data["total_capital_ratio"] = 0.0
        bs_data["nsfr"] = 0.0
        bs_data["lcr"] = 0.0

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
