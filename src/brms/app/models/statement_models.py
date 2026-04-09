"""Qt item models for financial statement tree views."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from PySide6.QtCore import QAbstractItemModel, QModelIndex, Qt

from brms.core.models.accounting.accounts import CompositeTAccount, TAccount

if TYPE_CHECKING:
    from brms.core.models.accounting.chart_of_accounts import ChartOfAccounts

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

    def _node(self, index: QModelIndex) -> _Row:
        if index.isValid():
            return index.internalPointer()
        return self._root

    def reset(self) -> None:
        """Clear all rows from the model."""
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


class BalanceSheetModel(_StatementModel):
    """Tree: Assets/Liabilities/Equity sections with expandable composite accounts."""

    _SECTION_CONFIG: ClassVar[list[tuple[str, str, str]]] = [
        ("Assets", "assets", "Total Assets"),
        ("Liabilities", "liabilities", "Total Liabilities"),
        ("Equity", "equities", "Total Equity"),
    ]

    def __init__(self) -> None:
        """Initialise with Account and Balance columns."""
        super().__init__(["Account", "Balance"])

    def update(self, chart: ChartOfAccounts) -> None:
        """Populate from a (closed) ChartOfAccounts, walking the account tree."""
        self.beginResetModel()
        self._root.children.clear()

        for section_label, attr, total_label in self._SECTION_CONFIG:
            section = _Row([section_label, None], bold=True)
            self._root.append(section)
            accounts: list[TAccount] = getattr(chart, attr)
            section_total = 0.0
            for acct in accounts:
                section_total += self._add_account(section, acct)
            # Retained Earnings is a separate field, not in the equities list
            if attr == "equities":
                re_acct = chart.retained_earnings_account
                re_bal = re_acct.balance()
                if re_bal != 0.0:
                    section.append(_Row([re_acct.name, re_bal]))
                    section_total += re_bal
            section.append(_Row([total_label, section_total], bold=True))

        self.endResetModel()

    def _add_account(self, parent_row: _Row, account: TAccount) -> float:
        """Recursively add an account and its children. Returns the account balance."""
        balance = account.balance()
        is_composite = isinstance(account, CompositeTAccount) and list(account.sub_accounts)

        if account.is_temporary_account:
            return 0.0
        if not is_composite and balance == 0.0:
            return 0.0
        if account.is_contra_account and balance == 0.0:
            return 0.0

        row = _Row([account.name, balance])
        parent_row.append(row)

        if is_composite:
            for child in account.sub_accounts:
                self._add_account(row, child)

        # Add contra accounts as children
        for contra in account.contra_accounts:
            contra_bal = contra.balance()
            if contra_bal != 0.0:
                row.append(_Row([contra.name, -contra_bal]))

        return balance


class IncomeStatementModel(_StatementModel):
    """Tree: Income/Expenses sections + Net Income row."""

    def __init__(self) -> None:
        """Initialise with Account and Balance columns."""
        super().__init__(["Account", "Balance"])

    def update(self, chart: ChartOfAccounts) -> None:
        """Populate from an unclosed ChartOfAccounts."""
        self.beginResetModel()
        self._root.children.clear()

        # Income section
        income_section = _Row(["Income", None], bold=True)
        self._root.append(income_section)
        total_income = 0.0
        for acct in chart.income:
            if acct.is_temporary_account or acct.is_contra_account:
                continue
            total_income += self._add_account(income_section, acct)
        income_section.append(_Row(["Total Income", total_income], bold=True))

        # Expenses section — values shown as negative (brackets) since they reduce net income
        expense_section = _Row(["Expenses", None], bold=True)
        self._root.append(expense_section)
        total_expenses = 0.0
        for acct in chart.expenses:
            if acct.is_temporary_account or acct.is_contra_account:
                continue
            bal = self._add_account(expense_section, acct, negate=True)
            total_expenses += abs(bal)
        expense_section.append(_Row(["Total Expenses", -total_expenses], bold=True))

        # Net Income
        self._root.append(_Row(["Net Income", total_income - total_expenses], bold=True))

        self.endResetModel()

    def _add_account(self, parent_row: _Row, account: TAccount, *, negate: bool = False) -> float:
        """Recursively add an account. Returns display value (negated if requested)."""
        balance = account.balance()
        is_composite = isinstance(account, CompositeTAccount) and list(account.sub_accounts)

        if not is_composite and balance == 0.0:
            return 0.0

        display_value = -balance if negate else balance
        row = _Row([account.name, display_value])
        parent_row.append(row)

        if is_composite:
            for child in account.sub_accounts:
                self._add_account(row, child, negate=negate)

        return display_value
