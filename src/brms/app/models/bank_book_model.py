"""Qt item model for bank book tree views (Banking Book / Trading Book)."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QAbstractItemModel, QModelIndex, Qt

from brms.app.models.statement_models import BoldRole

_INVALID = QModelIndex()

HEADERS = ["Name", "Value"]
COL_NAME = 0
COL_VALUE = 1

# Custom role to retrieve the previous value (for green/red coloring)
OldValueRole = Qt.ItemDataRole.UserRole + 1


class _Row:
    """Internal node for the bank book tree."""

    __slots__ = ("bold", "children", "instrument_id", "old_value", "parent", "values")

    def __init__(
        self,
        values: list[Any],
        *,
        bold: bool = False,
        parent: _Row | None = None,
        instrument_id: str | None = None,
    ) -> None:
        self.values = values
        self.bold = bold
        self.parent = parent
        self.children: list[_Row] = []
        self.instrument_id = instrument_id
        self.old_value: float | None = None

    def append(self, child: _Row) -> None:
        """Append a child row, setting its parent."""
        child.parent = self
        self.children.append(child)

    def remove(self, child: _Row) -> None:
        """Remove a child row."""
        self.children.remove(child)
        child.parent = None

    def row_index(self) -> int:
        """Return the index of this row in its parent's children list."""
        if self.parent is not None:
            return self.parent.children.index(self)
        return 0


class BankBookModel(QAbstractItemModel):
    """Tree model for a single bank book (banking or trading).

    Structure:
        Assets (bold)
          ├─ Held-to-Maturity (bold)
          │   ├─ Bond A
          │   └─ Bond B
          └─ Loans & Mortgages (bold)
              └─ Loan C
        Liabilities (bold)
          └─ Deposits
        Equity (bold)
          └─ Common Equity
    """

    def __init__(self, *, include_equity: bool = True) -> None:
        """Initialize with permanent top-level nodes.

        Args:
            include_equity: Whether to include the Equity node (False for trading book).

        """
        super().__init__()
        self._headers = HEADERS
        self._root = _Row(HEADERS)
        # Permanent top-level nodes
        self._assets = _Row(["Assets", None], bold=True)
        self._liabilities = _Row(["Liabilities", None], bold=True)
        self._equity: _Row | None = _Row(["Equity", None], bold=True) if include_equity else None
        self._root.append(self._assets)
        self._root.append(self._liabilities)
        if self._equity is not None:
            self._root.append(self._equity)

    # ── Qt API ──────────────────────────────────────────────────────

    def columnCount(self, parent: QModelIndex = _INVALID) -> int:  # noqa: N802, ARG002
        """Return number of columns."""
        return len(self._headers)

    def rowCount(self, parent: QModelIndex = _INVALID) -> int:  # noqa: N802
        """Return number of rows under parent."""
        return len(self._node(parent).children)

    def index(self, row: int, column: int, parent: QModelIndex = _INVALID) -> QModelIndex:
        """Return a model index for the given row and column."""
        node = self._node(parent)
        if 0 <= row < len(node.children):
            return self.createIndex(row, column, node.children[row])
        return _INVALID

    def parent(self, index: QModelIndex = _INVALID) -> QModelIndex:  # type: ignore[override]
        """Return the parent index of the given index."""
        if not index.isValid():
            return _INVALID
        child: _Row = index.internalPointer()
        par = child.parent
        if par is None or par is self._root:
            return _INVALID
        return self.createIndex(par.row_index(), 0, par)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:  # noqa: ANN401
        """Return data for the given index and role."""
        if not index.isValid():
            return None
        node: _Row = index.internalPointer()
        if role == Qt.ItemDataRole.DisplayRole:
            col = index.column()
            if 0 <= col < len(node.values):
                return node.values[col]
            return None
        if role == BoldRole:
            return True if node.bold else None
        if role == OldValueRole and index.column() == COL_VALUE:
            return node.old_value
        return None

    def headerData(  # noqa: N802
        self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:  # noqa: ANN401
        """Return header data for the given section and orientation."""
        if orientation == Qt.Horizontal and 0 <= section < len(self._headers):
            if role == Qt.ItemDataRole.DisplayRole:
                return self._headers[section]
            if role == Qt.ItemDataRole.TextAlignmentRole and section > 0:
                return Qt.AlignRight | Qt.AlignVCenter
        return None

    def flags(self, index: QModelIndex = _INVALID) -> Qt.ItemFlag:
        """Return item flags for the given index."""
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

    # ── Helpers ─────────────────────────────────────────────────────

    def _node(self, index: QModelIndex) -> _Row:
        if index.isValid():
            return index.internalPointer()
        return self._root

    @property
    def assets(self) -> _Row:
        """The Assets top-level node."""
        return self._assets

    @property
    def liabilities(self) -> _Row:
        """The Liabilities top-level node."""
        return self._liabilities

    @property
    def equity(self) -> _Row | None:
        """The Equity top-level node, or None for trading book."""
        return self._equity

    # ── Mutation API (used by controllers) ──────────────────────────

    def find_or_create_class_group(self, side_node: _Row, class_label: str) -> _Row:
        """Find an existing class group under a side node, or create one."""
        for child in side_node.children:
            if child.values[COL_NAME] == class_label:
                return child
        # Create new group
        parent_index = self._index_for_node(side_node)
        pos = len(side_node.children)
        self.beginInsertRows(parent_index, pos, pos)
        group = _Row([class_label, None], bold=True)
        side_node.append(group)
        self.endInsertRows()
        return group

    def add_instrument(
        self, group: _Row, name: str, value: float | None, instrument_id: str,
    ) -> None:
        """Add an instrument row under a class group node."""
        parent_index = self._index_for_node(group)
        pos = len(group.children)
        self.beginInsertRows(parent_index, pos, pos)
        group.append(_Row([name, value], instrument_id=instrument_id))
        self.endInsertRows()

    @property
    def _sides(self) -> tuple[_Row, ...]:
        """Return all active top-level side nodes."""
        if self._equity is not None:
            return (self._assets, self._liabilities, self._equity)
        return (self._assets, self._liabilities)

    def remove_instrument(self, instrument_id: str) -> bool:
        """Remove an instrument row by its instrument_id. Returns True if found."""
        for side in self._sides:
            for group in side.children:
                for child in group.children:
                    if child.instrument_id == instrument_id:
                        parent_index = self._index_for_node(group)
                        row = child.row_index()
                        self.beginRemoveRows(parent_index, row, row)
                        group.remove(child)
                        self.endRemoveRows()
                        return True
        return False

    def update_instrument_value(self, instrument_id: str, value: float) -> bool:
        """Update the value column for an instrument. Returns True if found."""
        node = self._find_instrument(instrument_id)
        if node is not None:
            node.old_value = node.values[COL_VALUE]
            node.values[COL_VALUE] = value
            idx = self._index_for_node(node)
            value_idx = self.createIndex(idx.row(), COL_VALUE, node)
            self.dataChanged.emit(value_idx, value_idx)
            return True
        return False

    def find_instrument_by_name(self, name: str) -> _Row | None:
        """Find an instrument row by name (used for Cash lookup)."""
        for side in self._sides:
            for group in side.children:
                for child in group.children:
                    if child.values[COL_NAME] == name:
                        return child
        return None

    def get_instrument_id(self, index: QModelIndex) -> str | None:
        """Get the instrument_id for a given index, or None if it's a group/header."""
        if not index.isValid():
            return None
        node: _Row = index.internalPointer()
        return node.instrument_id

    def clear_instruments(self) -> None:
        """Remove all instrument children from all top-level nodes."""
        self.beginResetModel()
        for side in self._sides:
            side.children.clear()
        self.endResetModel()

    # ── Private ─────────────────────────────────────────────────────

    def _find_instrument(self, instrument_id: str) -> _Row | None:
        """Find a row by instrument_id across all groups."""
        for side in self._sides:
            for group in side.children:
                for child in group.children:
                    if child.instrument_id == instrument_id:
                        return child
        return None

    def _index_for_node(self, node: _Row) -> QModelIndex:
        """Create a QModelIndex for a given _Row node."""
        if node is self._root:
            return _INVALID
        return self.createIndex(node.row_index(), 0, node)
