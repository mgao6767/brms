"""Controller for managing bank operations via core services and EventBus."""

from __future__ import annotations

from typing import TYPE_CHECKING

from brms.app.controllers.bank_book_controller import BankingBookController, TradingBookController
from brms.app.controllers.base import BRMSController
from brms.core.enums import BookType
from brms.core.enums import PositionSide as Position
from brms.core.events import InstrumentAdded, InstrumentRemoved

if TYPE_CHECKING:
    from brms.app.controllers.inspector_controller import InspectorController
    from brms.app.views.bank_book.combined_book_widget import BRMSCombinedBookWidget
    from brms.core.events import EventBus
    from brms.core.models.bank import Bank


class BankController(BRMSController):
    """Coordinator for banking/trading book controllers."""

    def __init__(
        self,
        bank: Bank,
        event_bus: EventBus,
        combined_book_view: BRMSCombinedBookWidget,
        inspector_ctrl: InspectorController,
    ) -> None:
        """Initialize the BankController with core services."""
        super().__init__()
        self.bank = bank

        self.banking_book_ctrl = BankingBookController(
            bank.banking_book, combined_book_view.banking_tree,
            combined_book_view.banking_model, inspector_ctrl,
            event_bus, BookType.BANKING, bank.positions,
        )
        self.trading_book_ctrl = TradingBookController(
            bank.trading_book, combined_book_view.trading_tree,
            combined_book_view.trading_model, inspector_ctrl,
            event_bus, BookType.TRADING, bank.positions,
        )

        self._combined_view = combined_book_view
        event_bus.subscribe(InstrumentAdded, self._on_instrument_added)
        event_bus.subscribe(InstrumentRemoved, self._on_instrument_removed)
        self._populate_books()

    def reset(self) -> None:
        """Disconnect signals and clear all data from both book trees."""
        self.banking_book_ctrl.disconnect_signals()
        self.trading_book_ctrl.disconnect_signals()
        self.banking_book_ctrl.reset()
        self.trading_book_ctrl.reset()

    def _populate_books(self) -> None:
        """Populate the tree widgets with all existing instruments in the bank."""
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
            ctrl.add_instrument(
                instrument, side, initial_value=float(pos.acquisition_cost),
                measurement_basis=pos.measurement_basis,
            )
        self._combined_view.banking_tree.expandAll()
        self._combined_view.trading_tree.expandAll()

    def _on_instrument_added(self, event: InstrumentAdded) -> None:
        """Handle an instrument being added to a book."""
        position = Position.LONG
        if event.book_type == "banking":
            self.banking_book_ctrl.add_instrument(event.instrument, position)
        else:
            self.trading_book_ctrl.add_instrument(event.instrument, position)

    def _on_instrument_removed(self, event: InstrumentRemoved) -> None:
        """Handle an instrument being removed from a book."""
        position = Position.LONG
        if event.book_type == "banking":
            self.banking_book_ctrl.remove_instrument(event.instrument, position)
        else:
            self.trading_book_ctrl.remove_instrument(event.instrument, position)
