"""Interest Rate Risk tab — maturity gap table and bar chart."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PySide6.QtCore import QLocale, Qt
from PySide6.QtGui import QFont, QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QHeaderView,
    QSplitter,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

from brms.app.views.styler import BRMSStyler

if TYPE_CHECKING:
    from brms.core.metrics.risk.interest_rate_risk.maturity_gap import MaturityGapResult

_locale = QLocale()
_COLUMNS = ["Bucket", "RSA", "RSL", "Gap", "Cumulative Gap", "\u0394NII (+200bp)", "\u0394NII (-200bp)"]
_MILLIONS = 1_000_000
_THOUSANDS = 1_000


class BRMSInterestRateRiskWidget(QWidget):
    """Maturity gap table and bar chart for IRRBB."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the interest rate risk widget."""
        super().__init__(parent)
        self.styler = BRMSStyler.instance()

        # Table model
        self._model = QStandardItemModel()
        self._model.setHorizontalHeaderLabels(_COLUMNS)

        self._tree = QTreeView()
        self._tree.setModel(self._model)
        self._tree.setAlternatingRowColors(True)
        self._tree.setEditTriggers(QTreeView.EditTrigger.NoEditTriggers)
        self._tree.setSelectionBehavior(QTreeView.SelectionBehavior.SelectRows)
        self._tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for col in range(1, len(_COLUMNS)):
            self._tree.header().setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)

        # Bar chart
        fig = Figure(figsize=(6, 4), facecolor=self.styler.plot_background_color)
        fig.subplots_adjust(left=0.12, right=0.95, top=0.9, bottom=0.25)
        self._canvas = FigureCanvas(fig)
        self._ax = fig.add_subplot()
        self._ax.set_title("Maturity Gap by Time Bucket", fontsize=10, fontweight="bold", loc="left")
        self._ax.grid(visible=True, axis="y", linestyle="--", alpha=0.4)
        self.styler.style_changed.connect(self._update_style)

        # Layout
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._tree)
        chart_widget = QWidget()
        chart_layout = QVBoxLayout(chart_widget)
        chart_layout.setContentsMargins(0, 0, 0, 0)
        chart_layout.addWidget(self._canvas)
        splitter.addWidget(chart_widget)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addWidget(splitter)

    def _update_style(self) -> None:
        """Update chart background on theme change."""
        bg = self.styler.plot_background_color if self.styler.use_custom_style else "white"
        self._canvas.figure.patch.set_facecolor(bg)
        self._canvas.draw_idle()

    def update(self, result: MaturityGapResult) -> None:
        """Refresh table and chart from a MaturityGapResult."""
        self._update_table(result)
        self._update_chart(result)

    def _update_table(self, result: MaturityGapResult) -> None:
        """Populate the table model from result."""
        self._model.removeRows(0, self._model.rowCount())
        bold_font = QFont()
        bold_font.setBold(True)

        for i, bucket in enumerate(result.buckets):
            row = [
                QStandardItem(bucket.label),
                self._currency_item(result.rsa[i]),
                self._currency_item(result.rsl[i]),
                self._currency_item(result.gap[i]),
                self._currency_item(result.cumulative_gap[i]),
                self._currency_item(result.delta_nii_up[i]),
                self._currency_item(result.delta_nii_down[i]),
            ]
            self._model.appendRow(row)

        # Totals row
        totals = [
            QStandardItem("Total"),
            self._currency_item(result.total_rsa),
            self._currency_item(result.total_rsl),
            self._currency_item(result.total_gap),
            QStandardItem(""),
            self._currency_item(result.total_delta_nii_up),
            self._currency_item(result.total_delta_nii_down),
        ]
        for item in totals:
            item.setFont(bold_font)
        self._model.appendRow(totals)

    def _update_chart(self, result: MaturityGapResult) -> None:
        """Redraw the bar chart."""
        self._ax.clear()
        self._ax.set_title("Maturity Gap by Time Bucket", fontsize=10, fontweight="bold", loc="left")
        self._ax.grid(visible=True, axis="y", linestyle="--", alpha=0.4)

        labels = [b.label for b in result.buckets]
        gaps = result.gap
        x = np.arange(len(labels))
        colors = ["#3b82f6" if g >= 0 else "#ef4444" for g in gaps]

        self._ax.bar(x, gaps, color=colors, width=0.7)
        self._ax.set_xticks(x)
        self._ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=7)
        self._ax.axhline(y=0, color="gray", linewidth=0.5)

        # Y-axis formatting
        max_val = max(abs(g) for g in gaps) if any(g != 0 for g in gaps) else 1
        if max_val >= _MILLIONS:
            self._ax.yaxis.set_major_formatter(
                lambda val, _: _locale.toCurrencyString(val / _MILLIONS) + "M",
            )
        elif max_val >= _THOUSANDS:
            self._ax.yaxis.set_major_formatter(
                lambda val, _: _locale.toCurrencyString(val / _THOUSANDS) + "K",
            )

        self._canvas.draw()

    @staticmethod
    def _currency_item(value: float) -> QStandardItem:
        """Create a right-aligned currency-formatted item."""
        item = QStandardItem(_locale.toCurrencyString(value))
        item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        return item
