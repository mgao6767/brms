"""Delegates for financial statement tree views."""

from __future__ import annotations

from PySide6.QtCore import QLocale, QModelIndex, Qt
from PySide6.QtGui import QFont, QPainter
from PySide6.QtWidgets import QStyledItemDelegate, QStyleOptionViewItem

from brms.app.models.statement_models import BoldRole

LOCALE = QLocale.system()


class StatementCurrencyDelegate(QStyledItemDelegate):
    """Right-aligned currency formatting with red for negative values."""

    def initStyleOption(self, option: QStyleOptionViewItem, index: QModelIndex) -> None:  # noqa: N802
        """Set right-aligned display for currency columns."""
        super().initStyleOption(option, index)
        option.displayAlignment = Qt.AlignRight | Qt.AlignVCenter

    def displayText(self, value: object, locale: QLocale) -> str:  # noqa: N802, ARG002
        """Format numeric values as locale currency strings. Negatives shown in brackets."""
        if isinstance(value, int | float):
            if value < 0:
                return f"({LOCALE.toCurrencyString(abs(value))})"
            return LOCALE.toCurrencyString(value)
        return str(value) if value is not None else ""

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        """Paint with bold for header rows."""
        bold = index.data(BoldRole)
        if bold:
            option.font.setWeight(QFont.Weight.Bold)
        super().paint(painter, option, index)


class StatementAccountDelegate(QStyledItemDelegate):
    """Left-aligned account name, bold for section headers and totals."""

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        """Paint with bold text for section headers and totals."""
        bold = index.data(BoldRole)
        if bold:
            option.font.setWeight(QFont.Weight.Bold)
        super().paint(painter, option, index)
