"""Flat table model for transaction history — O(1) insertion via QTableView."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt

_HEADERS = ("Tx#", "Date", "Type", "Instrument", "Value", "Description", "ID")
_ROOT = QModelIndex()


class TransactionTableModel(QAbstractTableModel):
    """Flat list-backed model. Each row is a tuple; no per-row objects."""

    def __init__(self, parent: Any = None) -> None:  # noqa: ANN401
        """Initialize with an empty row list."""
        super().__init__(parent)
        self._rows: list[tuple] = []

    def rowCount(self, parent: QModelIndex = _ROOT) -> int:  # noqa: N802
        """Return total row count."""
        if parent.isValid():
            return 0
        return len(self._rows)

    def columnCount(self, parent: QModelIndex = _ROOT) -> int:  # noqa: N802
        """Return column count."""
        if parent.isValid():
            return 0
        return len(_HEADERS)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:  # noqa: ANN401
        """Return cell data for the given index and role."""
        if not index.isValid() or role != Qt.ItemDataRole.DisplayRole:
            return None
        return self._rows[index.row()][index.column()]

    def headerData(  # noqa: N802
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> str | None:
        """Return column header labels."""
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return _HEADERS[section]
        return None

    def row_data(self, row: int) -> tuple:
        """Direct access to a row tuple (for filter checks and selection)."""
        return self._rows[row]

    def append_rows(self, rows: list[tuple]) -> None:
        """Append rows in a single beginInsertRows/endInsertRows pair."""
        if not rows:
            return
        first = len(self._rows)
        self.beginInsertRows(QModelIndex(), first, first + len(rows) - 1)
        self._rows.extend(rows)
        self.endInsertRows()

    def clear(self) -> None:
        """Remove all rows."""
        self.beginResetModel()
        self._rows.clear()
        self.endResetModel()
