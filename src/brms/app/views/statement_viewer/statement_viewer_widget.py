"""Statement viewer: tabbed QTreeView widgets for Trial Balance, Income Statement, Balance Sheet."""

from __future__ import annotations

import qtawesome as qta
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHeaderView,
    QTabWidget,
    QToolBar,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

from brms.app.models.statement_models import (
    BalanceSheetModel,
    IncomeStatementModel,
    TrialBalanceModel,
)
from brms.app.views.statement_viewer.delegates import (
    StatementAccountDelegate,
    StatementCurrencyDelegate,
)


class _StatementTab(QWidget):
    """A single statement tab: toolbar with export action + QTreeView."""

    def __init__(self, tree: QTreeView, parent: QWidget | None = None) -> None:
        """Initialise with a pre-built tree view."""
        super().__init__(parent)
        self.tree = tree
        self.toolbar = QToolBar()
        self.toolbar.setMovable(False)
        self.toolbar.setFloatable(False)
        self.toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.export_action = self.toolbar.addAction(qta.icon("mdi6.export"), "Export")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.toolbar)
        layout.addWidget(self.tree)


def _make_tree(model: object, column_count: int) -> QTreeView:
    """Create a configured QTreeView for a statement model."""
    tree = QTreeView()
    tree.setModel(model)
    tree.setAlternatingRowColors(True)
    tree.setSelectionBehavior(QTreeView.SelectionBehavior.SelectRows)
    tree.setEditTriggers(QTreeView.EditTrigger.NoEditTriggers)
    tree.header().setStretchLastSection(True)
    tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
    for col in range(1, column_count):
        tree.header().setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
    tree.setItemDelegateForColumn(0, StatementAccountDelegate(tree))
    for col in range(1, column_count):
        tree.setItemDelegateForColumn(col, StatementCurrencyDelegate(tree))
    return tree


class BRMSStatementViewer(QWidget):
    """Tabbed widget showing Trial Balance, Income Statement, and Balance Sheet as tree views."""

    export_requested = Signal(str)  # emits statement type key: "trial_balance", etc.

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialise tabs and models."""
        super().__init__(parent)

        # Models
        self.trial_balance_model = TrialBalanceModel()
        self.income_statement_model = IncomeStatementModel()
        self.balance_sheet_model = BalanceSheetModel()

        # Trees
        tb_tree = _make_tree(self.trial_balance_model, 3)
        is_tree = _make_tree(self.income_statement_model, 2)
        bs_tree = _make_tree(self.balance_sheet_model, 2)

        # Tabs
        self.trial_balance_tab = _StatementTab(tb_tree, self)
        self.income_statement_tab = _StatementTab(is_tree, self)
        self.balance_sheet_tab = _StatementTab(bs_tree, self)

        self._tabs = QTabWidget()
        self._tabs.addTab(self.trial_balance_tab, "Trial Balance")
        self._tabs.addTab(self.income_statement_tab, "Income Statement")
        self._tabs.addTab(self.balance_sheet_tab, "Balance Sheet")

        # Wire export actions to signal (connected once, view-owned)
        self.trial_balance_tab.export_action.triggered.connect(lambda: self.export_requested.emit("trial_balance"))
        self.income_statement_tab.export_action.triggered.connect(
            lambda: self.export_requested.emit("income_statement"),
        )
        self.balance_sheet_tab.export_action.triggered.connect(lambda: self.export_requested.emit("balance_sheet"))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._tabs)
