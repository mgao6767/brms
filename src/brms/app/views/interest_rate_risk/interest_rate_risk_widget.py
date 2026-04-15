"""Interest Rate Risk tab — sub-tabs for maturity gap and duration gap models."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import qtawesome as qta
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PySide6.QtCore import QLocale, Qt
from PySide6.QtGui import QAction, QFont, QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QFileDialog,
    QHeaderView,
    QLabel,
    QSplitter,
    QTabWidget,
    QToolBar,
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


class MaturityGapWidget(QWidget):
    """Maturity gap table and bar chart for IRRBB."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the maturity gap widget."""
        super().__init__(parent)
        self.styler = BRMSStyler.instance()

        # Toolbar
        self._toolbar = QToolBar()
        self._toolbar.setMovable(False)
        self._toolbar.setFloatable(False)
        self._toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)

        self._table_action = QAction(qta.icon("mdi6.table-of-contents"), "Show Table", self)
        self._figure_action = QAction(qta.icon("mdi6.chart-bell-curve-cumulative"), "Show Plot", self)
        self._all_view_action = QAction(qta.icon("mdi.chart-multiple"), "Show Both", self)
        self._save_action = QAction(qta.icon("mdi6.export"), "Export Plot", self)

        self._table_action.setCheckable(True)
        self._figure_action.setCheckable(True)
        self._all_view_action.setCheckable(True)

        self._toolbar.addAction(self._table_action)
        self._toolbar.addAction(self._figure_action)
        self._toolbar.addAction(self._all_view_action)
        self._toolbar.addAction(self._save_action)

        self._table_action.triggered.connect(self._set_table_view)
        self._figure_action.triggered.connect(self._set_figure_view)
        self._all_view_action.triggered.connect(self._set_both_view)
        self._save_action.triggered.connect(self._export_plot)

        # Table model
        self._model = QStandardItemModel()
        self._model.setHorizontalHeaderLabels(_COLUMNS)

        self._tree = QTreeView()
        self._tree.setModel(self._model)
        self._tree.setAlternatingRowColors(True)
        self._tree.setEditTriggers(QTreeView.EditTrigger.NoEditTriggers)
        self._tree.setSelectionBehavior(QTreeView.SelectionBehavior.SelectRows)
        self._tree.header().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        # Bar chart
        fig = Figure(figsize=(6, 4), facecolor=self.styler.plot_background_color)
        fig.subplots_adjust(left=0.12, right=0.95, top=0.9, bottom=0.25)
        self._canvas = FigureCanvas(fig)
        self._ax = fig.add_subplot()
        self._ax.set_title("Maturity Gap by Time Bucket", fontsize=10, fontweight="bold", loc="left")
        self._ax.grid(visible=True, axis="y", linestyle="--", alpha=0.4)
        self.styler.style_changed.connect(self._update_style)

        # Splitter
        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        self._splitter.addWidget(self._tree)
        chart_widget = QWidget()
        chart_layout = QVBoxLayout(chart_widget)
        chart_layout.setContentsMargins(0, 0, 0, 0)
        chart_layout.addWidget(self._canvas)
        self._splitter.addWidget(chart_widget)

        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._toolbar)
        layout.addWidget(self._splitter)

        # Default to table-only view
        self._set_table_view()

    def _set_table_view(self) -> None:
        """Show table only."""
        self._table_action.setChecked(True)
        self._figure_action.setChecked(False)
        self._all_view_action.setChecked(False)
        self._splitter.setSizes([1, 0])

    def _set_figure_view(self) -> None:
        """Show plot only."""
        self._figure_action.setChecked(True)
        self._table_action.setChecked(False)
        self._all_view_action.setChecked(False)
        self._splitter.setSizes([0, 1])

    def _set_both_view(self) -> None:
        """Show table and plot side by side."""
        self._all_view_action.setChecked(True)
        self._figure_action.setChecked(False)
        self._table_action.setChecked(False)
        total_size = 1000
        self._splitter.setSizes([total_size // 2, total_size - total_size // 2])

    def _export_plot(self) -> None:
        """Save the bar chart to a file."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            caption="Save Plot",
            filter="PNG Files (*.png);;All Files (*)",
        )
        if file_path:
            self._canvas.figure.savefig(file_path)

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


class BRMSInterestRateRiskWidget(QWidget):
    """Container for Interest Rate Risk sub-tabs."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the interest rate risk container with sub-tabs."""
        super().__init__(parent)
        self._tab_widget = QTabWidget()

        # Sub-tabs
        self._maturity_gap_tab = MaturityGapWidget()
        self._duration_gap_tab = QWidget()

        # Duration Gap placeholder
        placeholder_layout = QVBoxLayout(self._duration_gap_tab)
        label = QLabel("Duration Gap Model")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder_layout.addWidget(label)

        self._tab_widget.addTab(self._maturity_gap_tab, "Maturity Gap")
        self._tab_widget.addTab(self._duration_gap_tab, "Duration Gap")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._tab_widget)

    def update(self, result: MaturityGapResult) -> None:
        """Forward maturity gap result to the maturity gap sub-tab."""
        self._maturity_gap_tab.update(result)
