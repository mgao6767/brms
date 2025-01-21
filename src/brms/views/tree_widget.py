"""Provides a custom QTreeView widget and a tree model to display hierarchical data."""

import uuid
from typing import Any, Optional

from PySide6.QtCore import QAbstractItemModel, QModelIndex, QPersistentModelIndex, Qt
from PySide6.QtWidgets import QAbstractItemView, QHeaderView, QTreeView, QVBoxLayout, QWidget

__all__ = [
    "BRMSTreeWidget",
]

TreeItemDataType = str
ModelIndex = QModelIndex | QPersistentModelIndex

QMODELINDEX = QModelIndex()


class TreeItem:
    """TreeItem represents a single item in a tree structure."""

    def __init__(self, data: list[TreeItemDataType], parent: Optional["TreeItem"] = None) -> None:
        """Initialize a TreeItem."""
        self.parent_item = parent
        self.item_data = data
        self.child_items: list[TreeItem] = []

    def append_child(self, item: "TreeItem") -> None:
        """Append a child item to this item."""
        self.child_items.append(item)

    def child(self, row: int) -> "TreeItem":
        """Return the child item at the given row."""
        return self.child_items[row]

    def child_count(self) -> int:
        """Return the number of child items."""
        return len(self.child_items)

    def column_count(self) -> int:
        """Return the number of columns."""
        return len(self.item_data)

    def data(self, column: int) -> TreeItemDataType | None:
        """Return the data for the given column."""
        if column < 0 or column >= len(self.item_data):
            return None
        return self.item_data[column]

    def parent(self) -> Optional["TreeItem"]:
        """Return the parent item."""
        return self.parent_item

    def row(self) -> int:
        """Return the row number of this item."""
        if self.parent_item:
            return self.parent_item.child_items.index(self)
        return 0


class TreeModel(QAbstractItemModel):
    """TreeModel provides a model for a tree structure to be used with QTreeView."""

    def __init__(self, headers: list[TreeItemDataType], parent: QWidget | None = None) -> None:
        """Initialize a TreeModel."""
        super().__init__(parent)
        self.root_item = TreeItem(headers)

    def columnCount(self, parent: ModelIndex = QMODELINDEX) -> int:  # noqa: N802
        """Return the number of columns."""
        if parent.isValid():
            return parent.internalPointer().column_count()
        return self.root_item.column_count()

    def rowCount(self, parent: ModelIndex = QMODELINDEX) -> int:  # noqa: N802
        """Return the number of rows."""
        if parent.isValid():
            return parent.internalPointer().child_count()
        return self.root_item.child_count()

    def data(self, index: ModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> str | None:
        """Return the data stored under the given role for the item referred to by the index."""
        if not index.isValid():
            return None
        match role:
            case Qt.ItemDataRole.DisplayRole:
                item = index.internalPointer()
                return str(item.data(index.column()))
            case _:
                return None

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole) -> Any:  # noqa: ANN401, N802
        """Return the header data for the given section, orientation, and role."""
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self.root_item.data(section)
        return None

    def flags(self, index: ModelIndex = QMODELINDEX) -> Qt.ItemFlag:
        """Return the item flags for the given index."""
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

    def parent(self, child: ModelIndex = QMODELINDEX) -> QModelIndex:  # type: ignore[override]
        """Return the parent index of the given child index."""
        if not child.isValid():
            return QModelIndex()
        child_item = child.internalPointer()
        if (parent_item := child_item.parent()) == self.root_item:
            return QModelIndex()
        return self.createIndex(parent_item.row(), 0, parent_item)

    def index(self, row: int, column: int, parent: ModelIndex = QMODELINDEX) -> QModelIndex:
        """Return the index of the item in the model specified by the given row, column, and parent index."""
        if not self.hasIndex(row, column, parent):
            return QModelIndex()
        parent_item = self.root_item if not parent.isValid() else parent.internalPointer()
        if child_item := parent_item.child(row):
            return self.createIndex(row, column, child_item)
        return QModelIndex()

    def add_data(self, parent: QModelIndex, data: list[dict]) -> None:
        """Add data to the tree model.

        `data` is a list of dictionaries, where each dictionary represents a row with multiple columns.
        Each dictionary can have a special key `_children` to hold sub-items.
        """
        parent_item = self.root_item if not parent.isValid() else parent.internalPointer()
        for row_data in data:
            # Get the values in the dictionary by order
            child_item = TreeItem(list(row_data.values()), parent_item)
            parent_item.append_child(child_item)
            if "_children" in row_data:
                self.add_data(self.createIndex(parent_item.child_count() - 1, 0, child_item), row_data["_children"])

    def remove_data(self, parent: QModelIndex, id: uuid.UUID, id_column: int = 0) -> None:
        """Remove data from the tree model based on id."""
        parent_item = self.root_item if not parent.isValid() else parent.internalPointer()
        for i, child in enumerate(parent_item.child_items):
            if child.data(id_column) == id:  # id is stored in the first column which should be hidden
                self.beginRemoveRows(parent, i, i)
                parent_item.child_items.pop(i)
                self.endRemoveRows()
                return
            if child.child_count() > 0:
                self.remove_data(self.createIndex(i, 0, child), id)


class BRMSTreeWidget(QTreeView):
    """BRMSTreeWidget is a QTreeView that displays a tree structure with custom data."""

    def __init__(self, columns: list[str], parent: QWidget | None = None) -> None:
        """Initialize the CustomTreeWidget."""
        super().__init__(parent)
        self.tree_model = TreeModel(columns)
        self.setModel(self.tree_model)
        self.setAlternatingRowColors(True)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.header().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)

    def populate_data(
        self, data: dict[str, str | object] | list[dict], *, clear_existing: bool = True, expand: bool = True
    ) -> None:
        """Add data to the tree."""
        if clear_existing:
            self.clear_data()
        data = [data] if isinstance(data, dict) else data
        self.tree_model.add_data(QModelIndex(), data)
        if expand:
            self.expandAll()

    def clear_data(self) -> None:
        """Clear all data from the tree."""
        self.tree_model.beginResetModel()
        self.tree_model.root_item.child_items.clear()
        self.tree_model.endResetModel()
