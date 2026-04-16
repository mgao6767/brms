"""Combined bank book widget with Banking Book and Trading Book side by side."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QSplitter,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

from brms.app.models.bank_book_model import BankBookModel
from brms.app.views.bank_book.delegates import BookCurrencyDelegate, BookNameDelegate
from brms.app.views.styler import BRMSStyler


def _make_tree(model: BankBookModel) -> QTreeView:
    """Create a configured QTreeView for a bank book model."""
    tree = QTreeView()
    tree.setModel(model)
    tree.setAlternatingRowColors(True)
    tree.setSelectionBehavior(QTreeView.SelectionBehavior.SelectRows)
    tree.setEditTriggers(QTreeView.EditTrigger.NoEditTriggers)
    tree.header().setStretchLastSection(True)
    tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
    tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
    tree.setItemDelegateForColumn(0, BookNameDelegate(tree))
    tree.setItemDelegateForColumn(1, BookCurrencyDelegate(tree))
    tree.expandAll()
    return tree


class BRMSCombinedBookWidget(QWidget):
    """Single view with Banking Book (left) and Trading Book (right) trees."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the combined book widget."""
        super().__init__(parent)

        self.banking_model = BankBookModel()
        self.trading_model = BankBookModel(include_equity=False)

        self.banking_tree = _make_tree(self.banking_model)
        self.trading_tree = _make_tree(self.trading_model)

        # Banking Book panel (left)
        banking_label = QLabel("Banking Book")
        banking_label.setStyleSheet("font-weight: 600;")
        banking_panel = QWidget()
        banking_layout = QVBoxLayout(banking_panel)
        banking_layout.setContentsMargins(0, 0, 0, 0)
        banking_layout.addWidget(banking_label)
        banking_layout.addWidget(self.banking_tree)

        # Trading Book panel (right)
        trading_label = QLabel("Trading Book")
        trading_label.setStyleSheet("font-weight: 600;")
        trading_panel = QWidget()
        trading_layout = QVBoxLayout(trading_panel)
        trading_layout.setContentsMargins(0, 0, 0, 0)
        trading_layout.addWidget(trading_label)
        trading_layout.addWidget(self.trading_tree)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(banking_panel)
        splitter.addWidget(trading_panel)

        main_layout = QHBoxLayout(self)
        main_layout.addWidget(splitter)

        BRMSStyler.instance().tick_colors_changed.connect(self._refresh_tick_colors)

    def _refresh_tick_colors(self, _enabled: bool) -> None:  # noqa: FBT001
        """Repaint both trees when the tick-color toggle flips."""
        self.banking_tree.viewport().update()
        self.trading_tree.viewport().update()
