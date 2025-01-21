from typing import TYPE_CHECKING

from brms.controllers.base import BRMSController
from brms.controllers.inspector_controller import InspectorController
from brms.instruments.base import Instrument
from brms.models.bank import Bank
from brms.models.bank_book import BankBook, Position
from brms.views.bank_book_widget import AssetColumns, BRMSBankBookWidget, ColumnOrder, LiabilityColumns
from brms.views.tree_widget import QMODELINDEX, TreeModel

if TYPE_CHECKING:
    from PySide6.QtCore import QItemSelection


class BankController(BRMSController):
    """Controller for managing bank operations, including banking and trading books."""

    def __init__(
        self,
        bank: Bank,
        banking_book_view: BRMSBankBookWidget,
        trading_book_view: BRMSBankBookWidget,
        inspector_ctrl: InspectorController,
    ) -> None:
        super().__init__()
        self.bank = bank
        self.banking_book_view = banking_book_view
        self.trading_book_view = trading_book_view
        # Controllers passed in
        self.inspector_ctrl = inspector_ctrl
        # Sub controllers
        self.banking_book_ctrl = BankBookController(self.bank.banking_book, self.banking_book_view, self.inspector_ctrl)
        self.trading_book_ctrl = BankBookController(self.bank.trading_book, self.trading_book_view, self.inspector_ctrl)
        # Connect signals
        self.connect_signals()

    def add_instrument_to_banking_book(self, instrument: Instrument, position: Position) -> None:
        """Add an instrument to banking book based on position."""
        self.banking_book_ctrl.add_instrument(instrument, position)

    def add_instrument_to_trading_book(self, instrument: Instrument, position: Position) -> None:
        """Add an instrument to trading book based on position."""
        self.trading_book_ctrl.add_instrument(instrument, position)

    def remove_instrument_from_banking_book(self, instrument: Instrument, position: Position) -> None:
        """Remove an instrument from banking book based on position."""
        self.banking_book_ctrl.remove_instrument(instrument, position)

    def remove_instrument_from_trading_book(self, instrument: Instrument, position: Position) -> None:
        """Remove an instrument from trading book based on position."""
        self.trading_book_ctrl.remove_instrument(instrument, position)

    def connect_signals(self) -> None:
        """Connect signals to their respective slots."""
        pass


class BankBookController:
    """Controller for managing a bank's banking or trading book."""

    def __init__(self, bank_book: BankBook, view: BRMSBankBookWidget, inspector_ctrl: InspectorController) -> None:
        self.bank_book = bank_book
        self.bank_book_widget = view
        # Controllers passed in
        self.inspector_ctrl = inspector_ctrl
        # Pointers to TreeModel
        self.long_model: TreeModel = self.bank_book_widget.assets_tree.tree_model
        self.short_model: TreeModel = self.bank_book_widget.liabilities_tree.tree_model
        # Hide ID column since that instrument id is only used internally
        self.set_id_column_visibility(visible=False)
        self.connect_signals()

    @staticmethod
    def instrument_to_data(instrument: Instrument, position: Position) -> list[dict]:
        """Convert an instrument to data that can be used by the TreeModel."""
        data: dict[ColumnOrder, object]
        if position == Position.LONG:
            # Notably the dict can be constructed in any order as it will be sorted by column order required by the view
            data = {
                AssetColumns.ID: instrument.id,  # UUID is not displayable by TreeView
                AssetColumns.Asset: instrument.name,
                AssetColumns.Value: instrument.value,
            }
        elif position == Position.SHORT:
            data = {
                LiabilityColumns.ID: instrument.id,
                LiabilityColumns.Liability: instrument.name,
                LiabilityColumns.Value: instrument.value,
            }
        return [data]

    def add_instrument(self, instrument: Instrument, position: Position) -> None:
        """Add an instrument to the bank book."""
        self.bank_book.add_instrument(instrument, position)
        match position:
            case Position.LONG:
                self.long_model.add_data(QMODELINDEX, self.instrument_to_data(instrument, position))
            case Position.SHORT:
                self.short_model.add_data(QMODELINDEX, self.instrument_to_data(instrument, position))

    def remove_instrument(self, instrument: Instrument, position: Position) -> None:
        """Remove an instrument from the bank book."""
        self.bank_book.remove_instrument(instrument, position)
        match position:
            case Position.LONG:
                self.long_model.remove_data(QMODELINDEX, instrument.id, id_column=AssetColumns.ID.value)
            case Position.SHORT:
                self.short_model.remove_data(QMODELINDEX, instrument.id, id_column=LiabilityColumns.ID.value)

    def set_id_column_visibility(self, *, visible: bool) -> None:
        """Set the visibility of the ID column in the tree view."""
        self.bank_book_widget.assets_tree.setColumnHidden(AssetColumns.ID.value, not visible)
        self.bank_book_widget.liabilities_tree.setColumnHidden(LiabilityColumns.ID.value, not visible)

    def on_instrument_selected(
        self,
        selected: "QItemSelection",
        deselected: "QItemSelection",
        position: Position,
    ) -> None:
        """Slot to handle selection changes."""
        if position == Position.LONG:
            indexes = self.bank_book_widget.assets_tree.selectedIndexes()
            id_column = AssetColumns.ID.value
        else:
            indexes = self.bank_book_widget.liabilities_tree.selectedIndexes()
            id_column = LiabilityColumns.ID.value
        if indexes:
            selected_index = indexes[0]
            item = selected_index.internalPointer()
            instrument_id = item.data(id_column)
            if instrument := self.bank_book.get_instrument_by_id(instrument_id):
                self.inspector_ctrl.show_instrument_details(instrument)

    def connect_signals(self) -> None:
        """Connect signals to their respective slots."""
        self.bank_book_widget.assets_tree.selectionModel().selectionChanged.connect(
            lambda selected, deselected: self.on_instrument_selected(selected, deselected, Position.LONG),
        )
        self.bank_book_widget.liabilities_tree.selectionModel().selectionChanged.connect(
            lambda selected, deselected: self.on_instrument_selected(selected, deselected, Position.SHORT),
        )
