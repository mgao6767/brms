"""Interest Rate tab: table of benchmark rates on the left, time-series plot on the right."""

from __future__ import annotations

import datetime

import pandas as pd
import qtawesome as qta
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.dates import DAILY, AutoDateLocator, ConciseDateFormatter
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.ticker import FuncFormatter
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QCloseEvent, QShowEvent
from PySide6.QtWidgets import (
    QFileDialog,
    QHeaderView,
    QSplitter,
    QStyledItemDelegate,
    QTableView,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from brms.app.views.styler import BRMSStyler
from brms.app.views.widgets.popout import PopOutManager


class _RateItemDelegate(QStyledItemDelegate):
    def initStyleOption(self, option, index):  # noqa: N802
        super().initStyleOption(option, index)
        option.displayAlignment = Qt.AlignRight | Qt.AlignVCenter

    def displayText(self, value, locale):  # noqa: N802
        try:
            return locale.toString(value, "f", 2)
        except (ValueError, TypeError):
            return str(value)


class _RightAlignHeaderView(QHeaderView):
    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        self.setDefaultAlignment(Qt.AlignRight | Qt.AlignVCenter)


class TimeSeriesPlotWidget(QWidget):
    """Matplotlib time-series plot that extends as dates are added."""

    def __init__(self, title: str, line_labels: list[str], line_colors: list[str], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.styler = BRMSStyler.instance()
        self._title = title
        self._hidden_lines: set[str] = set()
        self._line_data: dict[str, tuple[list, list]] = {}
        self._legend_artist_to_title: dict[int, str] = {}
        self._annotations: list = []

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.control_toolbar = QToolBar(self)
        self.control_toolbar.setMovable(False)
        self.control_toolbar.setFloatable(False)
        self.control_toolbar.setContentsMargins(8, 2, 8, 2)
        spacer = QWidget()
        from PySide6.QtWidgets import QSizePolicy

        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.control_toolbar.addWidget(spacer)
        self.export_action = QAction(qta.icon("mdi6.export"), "Export", self)
        self.export_action.triggered.connect(self.export_plot)
        self.control_toolbar.addAction(self.export_action)
        self.control_toolbar.setVisible(False)
        root_layout.addWidget(self.control_toolbar)

        fig = Figure(figsize=(5, 3), facecolor=self.styler.plot_background_color)
        fig.subplots_adjust(left=0.08, right=0.92, top=0.92, bottom=0.18)
        self.canvas = FigureCanvas(fig)
        root_layout.addWidget(self.canvas)
        self.ax = fig.add_subplot()
        self.styler.style_axes(self.ax, title=title)

        locator = AutoDateLocator(minticks=2, maxticks=6)
        locator.intervald[DAILY] = [1, 2, 3, 5, 7, 14]
        self.ax.xaxis.set_major_locator(locator)
        self.ax.xaxis.set_major_formatter(ConciseDateFormatter(locator))
        self.ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:.2f}%"))

        self.lines: dict[str, Line2D] = {}
        for i, label in enumerate(line_labels):
            (line2d,) = self.ax.plot([], [], color=line_colors[i % len(line_colors)], label=label, linewidth=1.5)
            self.lines[label] = line2d

        self.styler.style_changed.connect(self._update_style)
        self.canvas.mpl_connect("pick_event", self._on_legend_pick)

    def update_plot(
        self,
        start_date: datetime.date,
        dates: list[datetime.date],
        data: dict[str, list[float]],
    ) -> None:
        """Update line data and redraw."""
        if not dates:
            return
        last = dates[-1]
        span = (last - start_date).days
        margin_days = max(30, int(span * 0.25))
        self.ax.set_xlim(pd.Timestamp(start_date), pd.Timestamp(last + datetime.timedelta(days=margin_days)))

        for label, values in data.items():
            if line2d := self.lines.get(label):
                self._line_data[label] = (dates, values)
                if label in self._hidden_lines:
                    line2d.set_data([], [])
                    line2d.set_visible(False)
                else:
                    line2d.set_data(dates, values)
                    line2d.set_visible(True)

        self.ax.relim()
        self.ax.autoscale_view(scalex=False)
        self._rebuild_legend()
        self._update_annotations(dates)
        self.canvas.draw_idle()

    def clear_plot(self) -> None:
        for line in self.lines.values():
            line.set_data([], [])
        self._line_data.clear()
        self.ax.relim()
        self.styler.style_axes(self.ax, title=self._title)
        self.canvas.draw_idle()

    def export_plot(self) -> None:
        default_name = f"BRMS - {self._title}.png"
        file_path, _ = QFileDialog.getSaveFileName(self, caption="Save Plot", dir=default_name, filter="PNG Files (*.png)")
        if file_path:
            self.canvas.figure.savefig(file_path)

    def _update_style(self) -> None:
        self.styler.style_figure(self.canvas.figure)
        self.styler.style_axes(self.ax)
        self.canvas.draw_idle()

    def _on_legend_pick(self, event: object) -> None:
        artist = event.artist  # type: ignore[attr-defined]
        title = self._legend_artist_to_title.get(id(artist))
        if title is None:
            return
        self._hidden_lines.symmetric_difference_update({title})
        self._apply_visibility()
        self.canvas.draw()

    def _apply_visibility(self) -> None:
        for title, line in self.lines.items():
            if title in self._hidden_lines:
                line.set_data([], [])
                line.set_visible(False)
            elif title in self._line_data:
                line.set_data(*self._line_data[title])
                line.set_visible(True)
        self.ax.relim()
        self.ax.autoscale_view()
        self._rebuild_legend()
        dates = next((d for d, _ in self._line_data.values()), [])
        self._update_annotations(dates)

    def _update_annotations(self, dates: list[datetime.date]) -> None:
        for ann in self._annotations:
            ann.remove()
        self._annotations.clear()
        if not dates:
            return
        last_date = dates[-1]
        for title, line in self.lines.items():
            if title in self._hidden_lines or not line.get_visible():
                continue
            ydata = line.get_ydata()
            if len(ydata) == 0:
                continue
            ann = self.ax.annotate(
                f"{ydata[-1]:.2f}%",
                xy=(last_date, ydata[-1]),
                xytext=(5, 0),
                textcoords="offset points",
                fontsize=7,
                color=line.get_color(),
                va="center",
                ha="left",
                fontweight="semibold",
            )
            self._annotations.append(ann)

    def _rebuild_legend(self) -> None:
        legend = self.styler.style_legend(self.ax)
        self._legend_artist_to_title.clear()
        for legend_line, legend_text, title in zip(
            legend.get_lines(), legend.get_texts(), self.lines.keys(), strict=False,
        ):
            legend_line.set_linewidth(3)
            legend_line.set_picker(8)
            legend_text.set_picker(8)
            self._legend_artist_to_title[id(legend_line)] = title
            self._legend_artist_to_title[id(legend_text)] = title
            alpha = 0.3 if title in self._hidden_lines else 1.0
            legend_line.set_alpha(alpha)
            legend_text.set_alpha(alpha)


class BRMSInterestRateWidget(QWidget):
    """Table + time-series plot for benchmark interest rates."""

    visibility_changed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.is_visible = False
        self.setWindowTitle("Interest Rate")
        styler = BRMSStyler.instance()

        self.toolbar = QToolBar()
        self.toolbar.setMovable(False)
        self.toolbar.setFloatable(False)
        self.toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.table_action = QAction(qta.icon("mdi6.table-of-contents"), "Show Table", self)
        self.figure_action = QAction(qta.icon("mdi6.chart-bell-curve-cumulative"), "Show Plot", self)
        self.all_view_action = QAction(qta.icon("mdi.chart-multiple"), "Show Both", self)
        self.pop_out_action = QAction(qta.icon("mdi6.open-in-new"), "Pop Out Plot", self)
        for act in (self.table_action, self.figure_action, self.all_view_action):
            act.setCheckable(True)
        self.toolbar.addAction(self.table_action)
        self.toolbar.addAction(self.figure_action)
        self.toolbar.addAction(self.all_view_action)
        self.toolbar.addAction(self.pop_out_action)

        self.table_view = QTableView()
        self.table_view.setHorizontalHeader(_RightAlignHeaderView(Qt.Horizontal))
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_view.setSelectionBehavior(QTableView.SelectRows)
        self.table_view.setItemDelegate(_RateItemDelegate())
        self.table_view.verticalHeader().setDefaultSectionSize(18)
        self.table_view.verticalHeader().setMinimumSectionSize(16)

        self.plot_widget = TimeSeriesPlotWidget(
            title="Interest Rate",
            line_labels=["Prime"],
            line_colors=[styler.chart_palette[0]],
            parent=self,
        )

        self.splitter = QSplitter()
        self.splitter.setOrientation(Qt.Orientation.Horizontal)
        self.splitter.addWidget(self.table_view)
        self.splitter.addWidget(self.plot_widget)

        layout = QVBoxLayout(self)
        layout.addWidget(self.toolbar)
        layout.addWidget(self.splitter)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.all_view_action.triggered.connect(self.set_default_view)
        self.table_action.triggered.connect(self.set_table_view)
        self.figure_action.triggered.connect(self.set_figure_view)
        self._popout = PopOutManager(self.plot_widget, self.splitter, title="Interest Rate -- Plot")
        self.pop_out_action.triggered.connect(self._popout.toggle)
        self._popout.popped_out.connect(self.plot_widget.control_toolbar.setVisible)
        self.set_default_view()

    def set_model(self, model) -> None:
        self.table_view.setModel(model)

    def set_default_view(self) -> None:
        self.all_view_action.setChecked(True)
        self.figure_action.setChecked(False)
        self.table_action.setChecked(False)
        self.splitter.setSizes([500, 500])

    def set_table_view(self) -> None:
        self.table_action.setChecked(True)
        self.figure_action.setChecked(False)
        self.all_view_action.setChecked(False)
        self.splitter.setSizes([1, 0])

    def set_figure_view(self) -> None:
        self.figure_action.setChecked(True)
        self.table_action.setChecked(False)
        self.all_view_action.setChecked(False)
        self.splitter.setSizes([0, 1])

    def showEvent(self, event: QShowEvent) -> None:  # noqa: N802
        self.is_visible = True
        self.visibility_changed.emit()
        super().showEvent(event)

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        self.is_visible = False
        self.visibility_changed.emit()
        super().closeEvent(event)
