"""Clipboard utilities for copying data from tree views and inspector."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

if TYPE_CHECKING:
    from PySide6.QtWidgets import QTreeView


def add_copy_context_menu(tree: QTreeView) -> None:
    """Attach a right-click context menu with Copy Value and Copy Row to a QTreeView."""
    from PySide6.QtGui import QAction
    from PySide6.QtWidgets import QMenu

    tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

    def _show_menu(pos: object) -> None:
        index = tree.indexAt(pos)  # type: ignore[arg-type]
        if not index.isValid():
            return
        menu = QMenu(tree)
        copy_val = QAction("Copy Value", menu)
        copy_val.triggered.connect(lambda: copy_tree_value(tree))
        menu.addAction(copy_val)
        copy_row_act = QAction("Copy Row", menu)
        copy_row_act.triggered.connect(lambda: copy_tree_row(tree))
        menu.addAction(copy_row_act)
        menu.exec(tree.viewport().mapToGlobal(pos))  # type: ignore[arg-type]

    tree.customContextMenuRequested.connect(_show_menu)


def copy_text(text: str) -> None:
    """Copy plain text to the system clipboard."""
    clipboard = QApplication.clipboard()
    if clipboard is not None:
        clipboard.setText(text)


def copy_tree_value(tree: QTreeView) -> None:
    """Copy the current cell's display text to the clipboard."""
    index = tree.currentIndex()
    if not index.isValid():
        return
    value = index.data(Qt.ItemDataRole.DisplayRole)
    if value is not None:
        copy_text(str(value))


def copy_tree_row(tree: QTreeView) -> None:
    """Copy all columns of the selected row as tab-separated text."""
    indexes = tree.selectedIndexes()
    if not indexes:
        return
    row_idx = indexes[0]
    model = tree.model()
    cols = model.columnCount()
    values = []
    for col in range(cols):
        idx = model.index(row_idx.row(), col, row_idx.parent())
        val = idx.data(Qt.ItemDataRole.DisplayRole)
        if val is not None:
            values.append(str(val))
        else:
            values.append("")
    copy_text("\t".join(values))


def copy_details(data: dict[str, Any]) -> None:
    r"""Copy a nested dict as tab-separated Property\tValue lines.

    Nested dicts are indented with two-space prefixes per level.
    """
    lines = _flatten_dict(data, indent=0)
    copy_text("\n".join(lines))


def _flatten_dict(data: dict[str, Any], indent: int) -> list[str]:
    """Recursively flatten a dict into tab-separated lines with indentation."""
    prefix = "  " * indent
    lines: list[str] = []
    for key, value in data.items():
        if isinstance(value, dict):
            lines.append(f"{prefix}{key}")
            lines.extend(_flatten_dict(value, indent + 1))
        else:
            lines.append(f"{prefix}{key}\t{value}")
    return lines
