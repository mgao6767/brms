"""Qt item models for financial statement tree views."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QAbstractItemModel, QModelIndex, Qt

# Qt.UserRole signals "this row should be bold" (section headers, totals)
BoldRole = Qt.ItemDataRole.UserRole

_INVALID = QModelIndex()


class _Row:
    """Internal node for statement tree models."""

    __slots__ = ("bold", "children", "parent", "values")

    def __init__(
        self, values: list[Any], *, bold: bool = False, parent: _Row | None = None,
    ) -> None:
        self.values = values
        self.bold = bold
        self.parent = parent
        self.children: list[_Row] = []

    def append(self, child: _Row) -> None:
        """Append a child row, setting its parent."""
        child.parent = self
        self.children.append(child)

    def row_index(self) -> int:
        """Return the index of this row in its parent's children list."""
        if self.parent is not None:
            return self.parent.children.index(self)
        return 0


class _StatementModel(QAbstractItemModel):
    """Base class for statement models with a flat or shallow tree of _Row nodes."""

    def __init__(self, headers: list[str]) -> None:
        super().__init__()
        self._headers = headers
        self._root = _Row(headers)

    def columnCount(self, parent: QModelIndex = _INVALID) -> int:  # noqa: N802, ARG002
        """Return number of columns."""
        return len(self._headers)

    def rowCount(self, parent: QModelIndex = _INVALID) -> int:  # noqa: N802
        """Return number of rows under parent."""
        node = self._node(parent)
        return len(node.children)

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
        return None

    def headerData(  # noqa: N802
        self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:  # noqa: ANN401
        """Return header data for the given section and orientation."""
        if orientation == Qt.Horizontal and role == Qt.ItemDataRole.DisplayRole and 0 <= section < len(self._headers):
            return self._headers[section]
        return None

    def flags(self, index: QModelIndex = _INVALID) -> Qt.ItemFlag:
        """Return item flags for the given index."""
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

    def _node(self, index: QModelIndex) -> _Row:
        if index.isValid():
            return index.internalPointer()
        return self._root

    def _reset(self) -> None:
        self.beginResetModel()
        self._root.children.clear()
        self.endResetModel()


class TrialBalanceModel(_StatementModel):
    """Flat table: Account | Debit | Credit, with a bold totals row."""

    def __init__(self) -> None:
        """Initialise with Account, Debit, Credit columns."""
        super().__init__(["Account", "Debit", "Credit"])

    def update(self, data: list[dict[str, Any]]) -> None:
        """Populate from ReportingService.trial_balance() output."""
        self.beginResetModel()
        self._root.children.clear()

        total_debit = 0.0
        total_credit = 0.0
        for row in data:
            debit = row["debit"]
            credit = row["credit"]
            if debit == 0.0 and credit == 0.0:
                continue
            self._root.append(_Row([row["account"], debit, credit]))
            total_debit += debit
            total_credit += credit

        self._root.append(_Row(["Total", total_debit, total_credit], bold=True))
        self.endResetModel()
