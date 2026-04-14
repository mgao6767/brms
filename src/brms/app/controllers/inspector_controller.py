"""Controller for the inspector dock — shows details for instruments and transactions."""

from __future__ import annotations

from typing import TYPE_CHECKING

from brms.app.controllers.base import BRMSController
from brms.core.visitors.inspection import InstrumentInspectionVisitor, TransactionInspectionVisitor

if TYPE_CHECKING:
    from typing import Any

    from brms.app.views.inspector import BRMSInspectorWidget
    from brms.core.models.accounting.journal import Journal
    from brms.core.models.bank import Bank
    from brms.core.models.instruments.base import Instrument
    from brms.core.models.transaction import Transaction


class InspectorController(BRMSController):
    """Controls the inspector dock, showing details for instruments and transactions."""

    def __init__(self, inspector_widget: BRMSInspectorWidget) -> None:
        """Initialize the inspector controller."""
        super().__init__()
        self.view = inspector_widget
        self._instrument_inspector = InstrumentInspectionVisitor()
        self._tx_inspector: TransactionInspectionVisitor | None = None
        self._last_details: dict[str, Any] = {}

    def bind_services(self, bank: Bank, journal: Journal) -> None:
        """Bind core services needed for transaction inspection."""
        self._tx_inspector = TransactionInspectionVisitor(bank, journal)

    def show_instrument_details(self, instrument: Instrument) -> None:
        """Show the details of the given instrument in the inspector view."""
        instrument.accept(self._instrument_inspector)
        self._last_details = self._instrument_inspector.get_result()
        data = self._format_for_tree(self._last_details)
        self.view.populate_data(data)

    def show_transaction_details(self, transaction: Transaction) -> None:
        """Show comprehensive transaction details in the inspector view."""
        if self._tx_inspector is None:
            return
        transaction.accept(self._tx_inspector)
        self._last_details = self._tx_inspector.get_result()
        data = self._format_for_tree(self._last_details)
        self.view.populate_data(data)

    def _format_for_tree(self, data: dict[str, Any]) -> list[dict]:
        """Convert a nested dictionary to a list of tree-view-ready dicts.

        Example::

            {"Prop": "Val"} → [{0: "Prop", 1: "Val"}]
            {"Group": {"Sub": "Val"}} → [{0: "Group", 1: "", "_children": [{0: "Sub", 1: "Val"}]}]

        """
        result = []
        for k, v in data.items():
            if isinstance(v, dict):
                result.append({0: k, 1: "", "_children": self._format_for_tree(v)})
            else:
                result.append({0: k, 1: v})
        return result

    def copy_details(self) -> None:
        """Copy the current inspector details to clipboard as tab-separated text."""
        from brms.app.clipboard import copy_details

        if self._last_details:
            copy_details(self._last_details)

    def connect_signals(self) -> None:
        """Connect context menu for copy actions on the inspector tree."""
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QMenu

        self.view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.view.customContextMenuRequested.connect(lambda pos: self._on_context_menu(pos, QMenu))

    def _on_context_menu(self, pos: object, menu_cls: type) -> None:
        """Show context menu with copy actions."""
        from PySide6.QtGui import QAction

        from brms.app.clipboard import copy_tree_row, copy_tree_value

        index = self.view.indexAt(pos)  # type: ignore[arg-type]
        if not index.isValid():
            return
        menu = menu_cls(self.view)
        copy_val = QAction("Copy Value", menu)
        copy_val.triggered.connect(lambda: copy_tree_value(self.view))
        menu.addAction(copy_val)
        copy_row_action = QAction("Copy Row", menu)
        copy_row_action.triggered.connect(lambda: copy_tree_row(self.view))
        menu.addAction(copy_row_action)
        copy_all = QAction("Copy All Details", menu)
        copy_all.triggered.connect(self.copy_details)
        menu.addAction(copy_all)
        menu.exec(self.view.viewport().mapToGlobal(pos))  # type: ignore[arg-type]
