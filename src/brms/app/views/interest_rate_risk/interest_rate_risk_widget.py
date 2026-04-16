"""Interest Rate Risk tab — sub-tabs for maturity gap and duration gap models."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import qtawesome as qta
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PySide6.QtCore import QLocale, Qt, QTimer
from PySide6.QtGui import QAction, QFont, QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QHeaderView,
    QLabel,
    QSizePolicy,
    QSplitter,
    QTabWidget,
    QToolBar,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

from brms.app.views.styler import BRMSStyler
from brms.app.views.widgets.popout import PopOutManager

if TYPE_CHECKING:
    from brms.core.metrics.risk.interest_rate_risk.maturity_gap import MaturityGapResult

_locale = QLocale()
_COLUMNS = ["Bucket", "RSA", "RSL", "Gap", "Cumulative Gap", "\u0394NII (+200bp)", "\u0394NII (-200bp)"]
_MILLIONS = 1_000_000
_THOUSANDS = 1_000


class MaturityGapWidget(QWidget):
    """Maturity gap table and bar chart for IRRBB."""

    def __init__(self, parent: QWidget | None = None) -> None:  # noqa: PLR0915
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
        self._pop_out_action = QAction(qta.icon("mdi6.open-in-new"), "Pop Out Plot", self)

        self._table_action.setCheckable(True)
        self._figure_action.setCheckable(True)
        self._all_view_action.setCheckable(True)

        self._toolbar.addAction(self._table_action)
        self._toolbar.addAction(self._figure_action)
        self._toolbar.addAction(self._all_view_action)
        self._toolbar.addAction(self._pop_out_action)

        self._table_action.triggered.connect(self._set_table_view)
        self._figure_action.triggered.connect(self._set_figure_view)
        self._all_view_action.triggered.connect(self._set_both_view)

        # Chart's own control panel (travels with the plot when popped out)
        self._chart_toolbar = QToolBar()
        self._chart_toolbar.setMovable(False)
        self._chart_toolbar.setFloatable(False)
        self._chart_toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        _left_pad = QWidget()
        _left_pad.setFixedWidth(6)
        self._chart_toolbar.addWidget(_left_pad)
        self._grid_checkbox = QCheckBox("Show Grid Lines")
        self._grid_checkbox.setChecked(True)
        self._grid_checkbox.toggled.connect(self._on_grid_toggled)
        self._chart_toolbar.addWidget(self._grid_checkbox)
        _spacer = QWidget()
        _spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._chart_toolbar.addWidget(_spacer)
        self._save_action = QAction(qta.icon("mdi6.export"), "Export", self)
        self._save_action.triggered.connect(self._export_plot)
        self._chart_toolbar.addAction(self._save_action)
        self._chart_toolbar.setVisible(False)  # only shown when popped out

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
        fig.subplots_adjust(left=0.12, right=0.95, top=0.92, bottom=0.25)
        self._canvas = FigureCanvas(fig)
        self._ax = fig.add_subplot()
        self.styler.style_axes(self._ax, title="Maturity Gap by Time Bucket")
        self.styler.style_changed.connect(self._update_style)
        # Flush any pending chart update once the canvas is actually sized
        self._canvas.mpl_connect("resize_event", self._on_canvas_resize)

        # Splitter
        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        self._splitter.addWidget(self._tree)
        self._chart_widget = QWidget()
        chart_layout = QVBoxLayout(self._chart_widget)
        chart_layout.setContentsMargins(0, 0, 0, 0)
        chart_layout.setSpacing(0)
        chart_layout.addWidget(self._chart_toolbar)
        chart_layout.addWidget(self._canvas)
        self._splitter.addWidget(self._chart_widget)

        # Pop-out
        self._popout = PopOutManager(self._chart_widget, self._splitter, title="Maturity Gap — Plot")
        self._pop_out_action.triggered.connect(self._popout.toggle)
        self._popout.popped_out.connect(self._chart_toolbar.setVisible)

        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._toolbar)
        layout.addWidget(self._splitter)

        self._last_result: MaturityGapResult | None = None
        self._chart_dirty = False

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
        # Defer so the splitter has time to resize the canvas before draw()
        QTimer.singleShot(0, self._flush_chart)

    def _set_both_view(self) -> None:
        """Show table and plot side by side."""
        self._all_view_action.setChecked(True)
        self._figure_action.setChecked(False)
        self._table_action.setChecked(False)
        total_size = 1000
        self._splitter.setSizes([total_size // 2, total_size - total_size // 2])
        QTimer.singleShot(0, self._flush_chart)

    def _flush_chart(self) -> None:
        """Redraw chart if data is pending and canvas is actually sized."""
        if not (self._chart_dirty and self._last_result is not None):
            return
        if self._canvas.width() <= 0 or self._canvas.height() <= 0:
            # Canvas not yet laid out — drawing now triggers LinAlgError.
            # Stay dirty; _on_canvas_resize will retry once Qt sizes us.
            return
        self._update_chart(self._last_result)
        self._chart_dirty = False

    def _on_canvas_resize(self, _event: object) -> None:
        """Retry pending flush once matplotlib reports a non-zero canvas size."""
        if self._chart_dirty and self._last_result is not None:
            QTimer.singleShot(0, self._flush_chart)

    def _on_grid_toggled(self, _checked: bool) -> None:  # noqa: FBT001
        """Toggle grid lines and redraw if we have data."""
        if self._last_result is not None and self._canvas.width() > 0:
            self._update_chart(self._last_result)

    def showEvent(self, event: object) -> None:  # noqa: N802
        """Flush any dirty chart data once the widget actually becomes visible."""
        super().showEvent(event)
        if self._chart_dirty and self._last_result is not None:
            QTimer.singleShot(0, self._flush_chart)

    def _export_plot(self) -> None:
        """Save the bar chart to a file."""
        plot_title = self._ax.get_title() or "Maturity Gap by Time Bucket"
        default_name = f"BRMS - {plot_title}.png"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            caption="Save Plot",
            dir=default_name,
            filter="PNG Files (*.png);;All Files (*)",
        )
        if file_path:
            self._canvas.figure.savefig(file_path)

    def _update_style(self) -> None:
        """Update chart background and axes colors to match the theme."""
        self.styler.style_figure(self._canvas.figure)
        self.styler.style_axes(self._ax)
        self._canvas.draw_idle()

    def _chart_visible(self) -> bool:
        """Return True if the chart panel is currently visible (embedded or popped out)."""
        return self._chart_widget.isVisible() and self._chart_widget.width() > 0

    def update(self, result: MaturityGapResult) -> None:
        """Refresh table and chart from a MaturityGapResult."""
        self._last_result = result
        self._update_table(result)
        if self._chart_visible():
            self._update_chart(result)
        else:
            self._chart_dirty = True

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
        self.styler.style_axes(
            self._ax, title="Maturity Gap by Time Bucket", show_grid=self._grid_checkbox.isChecked(),
        )

        labels = [b.label for b in result.buckets]
        gaps = result.gap
        x = np.arange(len(labels))
        colors = [self.styler.support_success if g >= 0 else self.styler.support_error for g in gaps]

        self._ax.bar(x, gaps, color=colors, width=0.7)
        self._ax.set_xticks(x)
        self._ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=7)
        self._ax.axhline(y=0, color=self.styler.text_muted, linewidth=0.5)

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
