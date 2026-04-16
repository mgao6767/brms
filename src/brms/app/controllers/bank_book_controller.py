"""Controller for managing bank book tree widgets."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu

from brms.app.controllers.base import BRMSController
from brms.app.views.bank_book.columns import AMORTIZED_COST_SUB_GROUPS, MEASUREMENT_BASIS_DISPLAY
from brms.core.enums import BookType, InstrumentType, MeasurementBasis, PositionStatus
from brms.core.enums import PositionSide as Position
from brms.core.events import ShowTransactionsRequested, ValuationsUpdated
from brms.core.models.instruments.deposits import Cash

if TYPE_CHECKING:
    from PySide6.QtWidgets import QTreeView

    from brms.app.controllers.inspector_controller import InspectorController
    from brms.app.models.bank_book_model import BankBookModel
    from brms.core.events import EventBus
    from brms.core.models.bank import BookView
    from brms.core.models.instruments.base import Instrument
    from brms.core.stores.position_store import PositionStore


class BankBookController(BRMSController):
    """Controller for managing a single book tree (banking or trading).

    Each tree has two top-level nodes: Assets (row 0) and Liabilities (row 1).
    Instruments are grouped by MeasurementBasis under the appropriate node.
    """

    def __init__(  # noqa: PLR0913
        self,
        bank_book: BookView,
        tree: QTreeView,
        model: BankBookModel,
        inspector_ctrl: InspectorController,
        event_bus: EventBus,
        book_type: BookType,
        position_store: PositionStore,
    ) -> None:
        """Initialize the bank book controller."""
        self.bank_book = bank_book
        self.tree = tree
        self.model = model
        self.inspector_ctrl = inspector_ctrl
        self._event_bus = event_bus
        self._book_type = book_type
        self._position_store = position_store
        event_bus.subscribe(ValuationsUpdated, self._on_valuations_updated)
        self.connect_signals()

    def reset(self) -> None:
        """Clear all instrument children from Assets and Liabilities nodes."""
        self.model.clear_instruments()
        self.tree.expandAll()

    def _on_valuations_updated(self, event: ValuationsUpdated) -> None:
        """Update instrument values and sync closed-flag from valuation event."""
        for pos in self._position_store.by_book(self._book_type):
            is_closed = pos.status == PositionStatus.CLOSED
            self.model.mark_instrument_closed(pos.instrument_id, is_closed)
            if is_closed:
                continue
            val = event.valuations.get(pos.id)
            if val is not None and float(val) != 0:
                self.model.update_instrument_value(pos.instrument_id, float(val))

    def _resolve_side_node(self, instrument: Instrument, position: Position) -> object:
        """Return the correct top-level node (Assets, Liabilities, or Equity)."""
        inst_type = getattr(instrument, "instrument_type", None)
        if inst_type == InstrumentType.COMMON_EQUITY:
            return self.model.equity
        if inst_type == InstrumentType.DEPOSIT:
            return self.model.liabilities
        return self.model.assets if position == Position.LONG else self.model.liabilities

    def add_instrument(
        self,
        instrument: Instrument,
        position: Position | None = None,
        initial_value: float | None = None,
        measurement_basis: MeasurementBasis | None = None,
    ) -> None:
        """Add an instrument under the appropriate class group node."""
        if position is None:
            position = Position.LONG
        side_node = self._resolve_side_node(instrument, position)
        inst_type = getattr(instrument, "instrument_type", None)
        basis = measurement_basis or getattr(instrument, "measurement_basis", None)

        # Deposits and equity use instrument type as group label
        if inst_type in (InstrumentType.DEPOSIT, InstrumentType.COMMON_EQUITY):
            class_label = "Deposits" if inst_type == InstrumentType.DEPOSIT else "Common Equity"
            group = self.model.find_or_create_class_group(side_node, class_label)
        elif basis == MeasurementBasis.AMORTIZED_COST:
            # 3-level: Amortized Cost → sub-group (HTM / Loans & Mortgages)
            basis_label = MEASUREMENT_BASIS_DISPLAY[MeasurementBasis.AMORTIZED_COST]
            basis_group = self.model.find_or_create_class_group(side_node, basis_label)
            sub_label = AMORTIZED_COST_SUB_GROUPS.get(inst_type, "Other")
            group = self.model.find_or_create_class_group(basis_group, sub_label)
        else:
            basis_label = MEASUREMENT_BASIS_DISPLAY.get(basis, str(basis)) if basis else "Other"
            group = self.model.find_or_create_class_group(side_node, basis_label)

        value = initial_value if initial_value is not None else getattr(instrument, "face_value", 0)
        self.model.add_instrument(group, instrument.name, float(value), instrument.id)
        self.tree.expandAll()

    def remove_instrument(self, instrument: Instrument, position: Position | None = None) -> None:  # noqa: ARG002
        """Remove an instrument from the tree model."""
        self.model.remove_instrument(instrument.id)

    def update_instrument(self, instrument: Instrument, position: Position | None = None) -> None:  # noqa: ARG002
        """Update an instrument's display in the tree model."""
        face_value = getattr(instrument, "face_value", 0)
        self.model.update_instrument_value(instrument.id, float(face_value))

    def update_instrument_value(self, instrument_id: str, value: float) -> None:
        """Update the displayed value for an instrument by its ID."""
        self.model.update_instrument_value(instrument_id, value)

    def _on_selection_changed(self, _selected: object, _deselected: object) -> None:
        """Slot to handle selection changes."""
        indexes = self.tree.selectedIndexes()
        if not indexes:
            return
        instrument_id = self.model.get_instrument_id(indexes[0])
        if instrument_id and (instrument := self.bank_book.get_instrument_by_id(instrument_id)):
            self.inspector_ctrl.show_instrument_details(instrument)

    def _on_context_menu(self, pos: QPoint) -> None:
        """Show context menu for the bank book tree."""
        index = self.tree.indexAt(pos)
        if not index.isValid():
            return
        instrument_id = self.model.get_instrument_id(index)
        if not instrument_id:
            return
        from brms.app.clipboard import copy_tree_row, copy_tree_value

        menu = QMenu(self.tree)
        action = QAction("Show Related Transactions", menu)
        action.triggered.connect(
            lambda: self._event_bus.emit(ShowTransactionsRequested(instrument_id=instrument_id)),
        )
        menu.addAction(action)
        menu.addSeparator()
        copy_val = QAction("Copy Value", menu)
        copy_val.triggered.connect(lambda: copy_tree_value(self.tree))
        menu.addAction(copy_val)
        copy_row_action = QAction("Copy Row", menu)
        copy_row_action.triggered.connect(lambda: copy_tree_row(self.tree))
        menu.addAction(copy_row_action)
        menu.exec(self.tree.viewport().mapToGlobal(pos))

    def connect_signals(self) -> None:
        """Connect signals to their respective slots."""
        self.tree.selectionModel().selectionChanged.connect(self._on_selection_changed)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._on_context_menu)

    def disconnect_signals(self) -> None:
        """Disconnect signals to prevent stale references on reload."""
        self.tree.selectionModel().selectionChanged.disconnect(self._on_selection_changed)
        self.tree.customContextMenuRequested.disconnect(self._on_context_menu)


class BankingBookController(BankBookController):
    """Controller for banking book."""

    def _add_cash(self, cash: Cash) -> None:
        """Add or update cash instrument in the Assets node."""
        row = self.model.find_instrument_by_name("Cash")
        if row is None:
            self.add_instrument(cash, Position.LONG)
            return
        # Update existing cash value
        cash_instrument = self.bank_book.get_instrument_by_id(row.instrument_id)
        if isinstance(cash_instrument, Cash):
            self.model.update_instrument_value(row.instrument_id, float(cash_instrument.value))

    def _remove_cash(self, _cash: Cash) -> None:
        """Update cash value when cash is removed."""
        row = self.model.find_instrument_by_name("Cash")
        if row is None:
            msg = "No cash in the asset tree model"
            raise ValueError(msg)
        cash_instrument = self.bank_book.get_instrument_by_id(row.instrument_id)
        if isinstance(cash_instrument, Cash):
            self.model.update_instrument_value(row.instrument_id, float(cash_instrument.value))

    def add_instrument(
        self,
        instrument: Instrument,
        position: Position | None = None,
        initial_value: float | None = None,
        measurement_basis: MeasurementBasis | None = None,
    ) -> None:
        """Add an instrument to the tree model."""
        if isinstance(instrument, Cash):
            self._add_cash(instrument)
            return
        super().add_instrument(instrument, position, initial_value=initial_value, measurement_basis=measurement_basis)

    def remove_instrument(self, instrument: Instrument, position: Position | None = None) -> None:
        """Remove an instrument from the tree model."""
        if isinstance(instrument, Cash):
            self._remove_cash(instrument)
            return
        super().remove_instrument(instrument, position)


class TradingBookController(BankBookController):
    """Controller for trading book."""
