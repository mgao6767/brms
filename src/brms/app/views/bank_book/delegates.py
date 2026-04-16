"""Delegates for bank book tree views."""

from __future__ import annotations

from PySide6.QtCore import QLocale, QModelIndex, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPalette
from PySide6.QtWidgets import QStyledItemDelegate, QStyleOptionViewItem

from brms.app.models.bank_book_model import OldValueRole
from brms.app.models.statement_models import BoldRole
from brms.app.views.styler import BRMSStyler

LOCALE = QLocale.system()


class BookNameDelegate(QStyledItemDelegate):
    """Left-aligned name column, bold for group/header rows."""

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        """Paint with bold for header rows."""
        if index.data(BoldRole):
            option.font.setWeight(QFont.Weight.Bold)
        super().paint(painter, option, index)


class BookCurrencyDelegate(QStyledItemDelegate):
    """Right-aligned currency column with bold for headers and color for value changes."""

    def initStyleOption(self, option: QStyleOptionViewItem, index: QModelIndex) -> None:  # noqa: N802
        """Right-align values."""
        super().initStyleOption(option, index)
        option.displayAlignment = Qt.AlignRight | Qt.AlignVCenter

    def displayText(self, value: object, locale: QLocale) -> str:  # noqa: N802, ARG002
        """Format numbers as currency."""
        if isinstance(value, int | float):
            return LOCALE.toCurrencyString(value)
        return str(value) if value is not None else ""

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        """Paint with bold for header rows, green/red for value changes."""
        if index.data(BoldRole):
            option.font.setWeight(QFont.Weight.Bold)
        else:
            current = index.data(Qt.ItemDataRole.DisplayRole)
            old = index.data(OldValueRole)
            if isinstance(current, int | float) and isinstance(old, int | float):
                styler = BRMSStyler.instance()
                if current > old:
                    option.palette.setColor(QPalette.ColorRole.Text, QColor(styler.support_success))
                elif current < old:
                    option.palette.setColor(QPalette.ColorRole.Text, QColor(styler.support_error))
        super().paint(painter, option, index)


# Alias used by transaction_history_widget
CurrencyDelegate = BookCurrencyDelegate
