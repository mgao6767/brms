"""Delegates and custom header for bank book views."""

import uuid

from PySide6.QtCore import QLocale, Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import (
    QHeaderView,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionHeader,
)

from brms.app.views.widgets.tree_widget import OldValueRole

LOCALE = QLocale.system()


class CurrencyDelegate(QStyledItemDelegate):
    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        option.displayAlignment = Qt.AlignRight | Qt.AlignVCenter

    def displayText(self, value, locale):
        """Format numbers as currency."""
        if isinstance(value, int | float):
            return LOCALE.toCurrencyString(value)
        return str(value)

    def paint(self, painter, option, index):
        """Customize text color for a specific column."""
        current_value = index.data(Qt.DisplayRole)
        old_value = index.data(OldValueRole)  # Get previous value from model
        if isinstance(current_value, int | float) and isinstance(old_value, int | float):
            if current_value >= old_value:
                option.palette.setColor(QPalette.Text, QColor("green"))  # Increased value
            elif current_value < old_value:
                option.palette.setColor(QPalette.Text, QColor("red"))  # Decreased value
        super().paint(painter, option, index)


class InstrumentIDDelegate(QStyledItemDelegate):
    def displayText(self, value, locale):
        """Format UUID as str."""
        if isinstance(value, uuid.UUID):
            return str(value)
        return super().displayText(value, locale)  # Default behavior


class CustomHeader(QHeaderView):
    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        self.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)  # Default left alignment
        self.text_padding = None  # Store dynamically calculated padding

    def paintSection(self, painter, rect, logicalIndex):
        """Preserve default styling but right-align the last column header text."""
        option = QStyleOptionHeader()
        self.initStyleOption(option)  # Get default styling
        option.rect = rect  # Set section rectangle
        option.section = logicalIndex  # Apply correct section index

        if logicalIndex < self.model().columnCount() - 1:
            # Store the text padding from a normal column (first column)
            super().paintSection(painter, rect, logicalIndex)

            if self.text_padding is None:  # Extract padding from the first column once
                text_rect = self.style().subElementRect(QStyle.SE_HeaderLabel, option, self)
                self.text_padding = text_rect.left() - rect.left()  # Extract left padding
        else:
            option.text = ""  # Remove default text drawing
            self.style().drawControl(QStyle.CE_HeaderSection, option, painter, self)  # Draw default header without text

            # Retrieve header text
            text = self.model().headerData(logicalIndex, Qt.Horizontal, Qt.DisplayRole)
            if text and self.text_padding is not None:
                painter.save()
                painter.setPen(self.palette().color(self.foregroundRole()))  # Keep text color

                # Apply the same padding as other columns (text_padding is dynamically calculated)
                adjusted_rect = rect.adjusted(self.text_padding, 0, -self.text_padding, 0)
                painter.drawText(adjusted_rect, Qt.AlignRight | Qt.AlignVCenter, text)

                painter.restore()
