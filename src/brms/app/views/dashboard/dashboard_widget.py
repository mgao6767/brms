"""Dashboard view — KPI cards, grouped detail cards, simulation strip, and chart grid."""

from __future__ import annotations

import datetime
from enum import Enum, auto
from typing import TYPE_CHECKING

import pandas as pd
from dateutil.relativedelta import relativedelta
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter
from PySide6.QtCore import QLocale, Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from brms.app.utils import pydate_to_qdate
from brms.app.views.styler import BRMSStyler

if TYPE_CHECKING:
    from matplotlib.lines import Line2D

_locale = QLocale()


class FormatType(Enum):
    """Format types for KPI values."""

    CURRENCY = auto()
    PERCENTAGE = auto()


# ---------------------------------------------------------------------------
# Formatters (shared by PlotWidget)
# ---------------------------------------------------------------------------


def _value_formatter(values: list[float]) -> FuncFormatter:
    """Return a FuncFormatter for formatting dollar values."""
    max_value = max(values, default=0)
    if max_value >= 1_000_000:
        return FuncFormatter(lambda x, _: _locale.toCurrencyString(x / 1_000_000) + "M")
    if max_value >= 1_000:
        return FuncFormatter(lambda x, _: _locale.toCurrencyString(x / 1_000) + "K")
    return FuncFormatter(lambda x, _: _locale.toCurrencyString(x))


def _ratio_formatter() -> FuncFormatter:
    """Return a FuncFormatter for formatting ratios as percentages."""
    return FuncFormatter(lambda x, _: f"{x * 100:.2f}%")


def _format_value(value: float | None, fmt: FormatType) -> str:
    """Format a metric value for display."""
    if value is None:
        return "\u2014"
    if fmt == FormatType.CURRENCY:
        return _locale.toCurrencyString(value)
    return f"{value * 100:.2f}%"


# ---------------------------------------------------------------------------
# KPIGroupCard
# ---------------------------------------------------------------------------


class KPIGroupCard(QFrame):
    """A card containing a header and a 2-column grid of labelled metric values."""

    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        """Initialize with a group title."""
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 6, 10, 6)
        outer.setSpacing(4)

        header = QLabel(title.upper())
        header.setStyleSheet(
            "font-size: 11px; font-weight: 700; letter-spacing: 0.5px; color: gray;"
            "border-bottom: 1px solid palette(mid); padding-bottom: 6px;",
        )
        header.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        outer.addWidget(header)

        self._grid = QGridLayout()
        self._grid.setSpacing(8)
        outer.addLayout(self._grid, 1)

        self._metrics: dict[str, tuple[QLabel, FormatType]] = {}
        self._row = 0
        self._col = 0

    def add_metric(self, key: str, label: str, format_type: FormatType) -> None:
        """Add a metric to the grid. Returns nothing — use set_value(key, val) to update."""
        title_lbl = QLabel(label)
        title_lbl.setStyleSheet("font-size: 12px; color: gray;")
        value_lbl = QLabel("\u2014")
        value_lbl.setStyleSheet("font-size: 13px; font-weight: 600;")

        cell = QVBoxLayout()
        cell.setSpacing(0)
        cell.addWidget(title_lbl)
        cell.addWidget(value_lbl)
        self._grid.addLayout(cell, self._row, self._col)

        self._metrics[key] = (value_lbl, format_type)
        self._grid.setRowStretch(self._row, 1)
        self._col += 1
        if self._col >= 2:  # noqa: PLR2004
            self._col = 0
            self._row += 1

    def set_value(self, key: str, value: float | None) -> None:
        """Update a metric value by key."""
        if entry := self._metrics.get(key):
            label, fmt = entry
            label.setText(_format_value(value, fmt))


# ---------------------------------------------------------------------------
# SimulationStrip
# ---------------------------------------------------------------------------


class SimulationStrip(QFrame):
    """Compact horizontal bar showing simulation date, period, and progress."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the simulation info strip."""
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setMaximumHeight(40)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 4, 12, 4)
        layout.setSpacing(12)

        # Date
        date_title = QLabel("DATE")
        date_title.setStyleSheet("font-size: 9px; font-weight: 600; color: gray; letter-spacing: 0.5px;")
        self._date_label = QLabel("\u2014")
        self._date_label.setStyleSheet("font-size: 12px; font-weight: 600;")
        layout.addWidget(date_title)
        layout.addWidget(self._date_label)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setFixedWidth(1)
        layout.addWidget(sep)

        # Period
        period_title = QLabel("PERIOD")
        period_title.setStyleSheet("font-size: 9px; font-weight: 600; color: gray; letter-spacing: 0.5px;")
        self._period_label = QLabel("\u2014")
        self._period_label.setStyleSheet("font-size: 10px;")
        layout.addWidget(period_title)
        layout.addWidget(self._period_label)

        # Progress
        layout.addStretch()
        self._progress_bar = QProgressBar()
        self._progress_bar.setValue(0)
        self._progress_bar.setFixedHeight(12)
        self._progress_bar.setMinimumWidth(120)
        self._progress_bar.setTextVisible(True)
        self._progress_bar.setFormat("%p%")
        layout.addWidget(self._progress_bar, 1)

    def set_date(self, date: datetime.date) -> None:
        """Update the current simulation date."""
        self._date_label.setText(pydate_to_qdate(date).toString(Qt.DateFormat.ISODate))

    def set_period(self, start: datetime.date, end: datetime.date) -> None:
        """Update the simulation period display."""
        s = pydate_to_qdate(start).toString(Qt.DateFormat.ISODate)
        e = pydate_to_qdate(end).toString(Qt.DateFormat.ISODate)
        self._period_label.setText(f"{s}  \u2192  {e}")

    def set_progress(self, percent: int) -> None:
        """Update the progress bar value."""
        self._progress_bar.setValue(percent)


# ---------------------------------------------------------------------------
# PlotWidget (reused from original, cleaned up)
# ---------------------------------------------------------------------------


class PlotWidget(QWidget):
    """Matplotlib-based time-series plot widget."""

    def __init__(
        self,
        title: str,
        line_titles: list[str],
        line_colors: list[str],
        *,
        use_ratio_formatter: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        """Initialize with title, line names, and colors."""
        super().__init__(parent)
        self.setMinimumHeight(200)
        self.styler = BRMSStyler.instance()
        self.start_date: datetime.date = datetime.date.today() - relativedelta(years=1)
        self.end_date: datetime.date = datetime.date.today()
        self.dates: list[datetime.date] = []
        self.use_ratio_formatter = use_ratio_formatter
        self.canvas = FigureCanvas(Figure(figsize=(5, 3), facecolor=self.styler.plot_background_color))
        self.ax = self.canvas.figure.add_subplot()
        self.ax.set_title(title, fontsize=10, fontweight="bold", loc="left", pad=8)
        self.ax.grid(visible=True, linestyle="--", alpha=0.4)
        self.ax.tick_params(axis="both", which="major", labelsize=9)
        self.formatter = _value_formatter([1_000_000]) if not use_ratio_formatter else _ratio_formatter()
        self.ax.yaxis.set_major_formatter(self.formatter)
        self.lines: dict[str, Line2D] = {}
        for i, line_title in enumerate(line_titles):
            (line2d,) = self.ax.plot([], [], color=line_colors[i], label=line_title, linewidth=1.5)
            self.lines[line_title] = line2d
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.canvas)
        self.styler.style_changed.connect(self.update_plot_style)
        # Legend toggle state
        self._hidden_lines: set[str] = set()
        self._line_data: dict[str, tuple] = {}  # title -> (xdata, ydata) last known
        self._legend_artist_to_title: dict = {}
        self.canvas.mpl_connect("pick_event", self._on_legend_pick)

    def _on_legend_pick(self, event: object) -> None:
        """Toggle visibility of a data line when its legend entry is clicked."""
        artist = event.artist  # type: ignore[attr-defined]
        title = self._legend_artist_to_title.get(id(artist))
        if title is None:
            return
        if title in self._hidden_lines:
            self._hidden_lines.discard(title)
        else:
            self._hidden_lines.add(title)
        self._apply_visibility()
        self.canvas.draw()

    def _apply_visibility(self) -> None:
        """Update line visibility from _hidden_lines, rescale, and rebuild legend."""
        for title, line in self.lines.items():
            if title in self._hidden_lines:
                line.set_data([], [])
                line.set_visible(False)
            elif title in self._line_data:
                line.set_data(*self._line_data[title])
                line.set_visible(True)
            else:
                line.set_visible(True)
        self.ax.relim()
        self.ax.autoscale_view()
        self._rebuild_legend()

    def update_plot_style(self) -> None:
        """Update figure background when the app style changes."""
        bg = self.styler.plot_background_color if self.styler.use_custom_style else "white"
        self.canvas.figure.patch.set_facecolor(bg)
        self.canvas.figure.canvas.draw_idle()

    def update_plot(
        self,
        start_date: datetime.date | None,
        end_date: datetime.date | None,
        dates: list[datetime.date],
        data: dict[str, list[float]],
    ) -> None:
        """Update line data and redraw the plot."""
        if not dates or start_date is None or end_date is None:
            return
        self.ax.set_xlim(pd.Timestamp(start_date), pd.Timestamp(end_date))
        for line_title, values in data.items():
            if line2d := self.lines.get(line_title):
                self._line_data[line_title] = (dates, values)
                if line_title in self._hidden_lines:
                    line2d.set_data([], [])
                    line2d.set_visible(False)
                else:
                    line2d.set_data(dates, values)
                    line2d.set_visible(True)
        self.ax.relim()
        self.ax.autoscale_view()
        # Update formatter based on visible data
        if not self.use_ratio_formatter:
            visible_vals = [v for t, vs in data.items() if t not in self._hidden_lines for v in vs]
            self.formatter = _value_formatter(visible_vals) if visible_vals else self.formatter
        self.ax.yaxis.set_major_formatter(self.formatter)
        if dates:
            self._rebuild_legend()
        self.canvas.draw_idle()

    def _rebuild_legend(self) -> None:
        """Rebuild the legend with pick support and correct alpha state."""
        legend = self.ax.legend(fontsize=9, loc="lower right", framealpha=0.9)
        self._legend_artist_to_title.clear()
        data_lines = list(self.lines.values())
        titles = list(self.lines.keys())
        for legend_line, legend_text, _data_line, title in zip(
            legend.get_lines(), legend.get_texts(), data_lines, titles, strict=False,
        ):
            legend_line.set_linewidth(3)
            legend_line.set_picker(8)
            legend_text.set_picker(8)
            self._legend_artist_to_title[id(legend_line)] = title
            self._legend_artist_to_title[id(legend_text)] = title
            alpha = 0.3 if title in self._hidden_lines else 1.0
            legend_line.set_alpha(alpha)
            legend_text.set_alpha(alpha)


# ---------------------------------------------------------------------------
# BRMSDashboard (main widget)
# ---------------------------------------------------------------------------


class BRMSDashboard(QWidget):
    """Card-based dashboard with KPIs, grouped details, and chart grid."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the dashboard layout."""
        super().__init__(parent)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(6)

        # Top: simulation strip spanning full width
        self.sim_strip = SimulationStrip()
        main_layout.addWidget(self.sim_strip)

        # Bottom: left cards + right charts
        body = QHBoxLayout()
        body.setSpacing(6)

        # Left panel: KPI cards + group cards
        left = QWidget()
        left.setFixedWidth(260)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(4)
        self._build_kpi_column(left_layout)
        self._build_group_column(left_layout)

        # Right panel: 2x2 chart grid
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        right_layout.addLayout(self._build_chart_grid())

        body.addWidget(left)
        body.addWidget(right, 1)
        main_layout.addLayout(body, 1)

    def _build_kpi_column(self, layout: QVBoxLayout) -> None:
        """Add the Balance Sheet group card to the given layout."""
        self.balance_sheet_group = KPIGroupCard("Balance Sheet")
        self.balance_sheet_group.add_metric("total_assets", "Total Assets", FormatType.CURRENCY)
        self.balance_sheet_group.add_metric("total_liabilities", "Total Liabilities", FormatType.CURRENCY)
        self.balance_sheet_group.add_metric("total_equity", "Total Equity", FormatType.CURRENCY)
        layout.addWidget(self.balance_sheet_group)

    def _build_group_column(self, layout: QVBoxLayout) -> None:
        """Add grouped detail cards vertically to the given layout."""
        self.capital_group = KPIGroupCard("Capital Adequacy")
        self.capital_group.add_metric("cet1_capital", "CET1 Capital", FormatType.CURRENCY)
        self.capital_group.add_metric("cet1_ratio", "CET1 Ratio", FormatType.PERCENTAGE)
        self.capital_group.add_metric("tier1_ratio", "Tier 1 Ratio", FormatType.PERCENTAGE)
        self.capital_group.add_metric("total_capital_ratio", "Total Capital Ratio", FormatType.PERCENTAGE)

        self.liquidity_group = KPIGroupCard("Liquidity & Risk")
        self.liquidity_group.add_metric("nsfr", "NSFR", FormatType.PERCENTAGE)
        self.liquidity_group.add_metric("lcr", "LCR", FormatType.PERCENTAGE)
        self.liquidity_group.add_metric("credit_rwa", "Credit RWA", FormatType.CURRENCY)
        self.liquidity_group.add_metric("op_rwa", "Op. RWA", FormatType.CURRENCY)

        self.profit_group = KPIGroupCard("Profitability")
        self.profit_group.add_metric("nim", "NIM", FormatType.PERCENTAGE)
        self.profit_group.add_metric("roa", "ROA", FormatType.PERCENTAGE)
        self.profit_group.add_metric("roe", "ROE", FormatType.PERCENTAGE)
        self.profit_group.add_metric("leverage_ratio", "Leverage Ratio", FormatType.PERCENTAGE)

        for grp in (self.capital_group, self.liquidity_group, self.profit_group):
            layout.addWidget(grp)

    def _build_chart_grid(self) -> QGridLayout:
        """Create the 2x2 chart grid."""
        grid = QGridLayout()
        grid.setSpacing(10)

        self.balance_sheet_plot = PlotWidget(
            title="Balance Sheet",
            line_titles=["Total Assets", "Total Liabilities", "Total Equity"],
            line_colors=["#3b82f6", "#ef4444", "#10b981"],
        )
        self.capital_ratio_plot = PlotWidget(
            title="Capital Ratios",
            line_titles=["CET1 Ratio"],
            line_colors=["#3b82f6"],
            use_ratio_formatter=True,
        )
        self.liquidity_plot = PlotWidget(
            title="Liquidity Ratios",
            line_titles=["NSFR", "LCR"],
            line_colors=["#0ea5e9", "#14b8a6"],
            use_ratio_formatter=True,
        )
        self.profitability_plot = PlotWidget(
            title="Profitability",
            line_titles=["NIM", "ROA", "ROE"],
            line_colors=["#f59e0b", "#10b981", "#ef4444"],
            use_ratio_formatter=True,
        )

        grid.addWidget(self.balance_sheet_plot, 0, 0)
        grid.addWidget(self.capital_ratio_plot, 0, 1)
        grid.addWidget(self.liquidity_plot, 1, 0)
        grid.addWidget(self.profitability_plot, 1, 1)
        return grid
