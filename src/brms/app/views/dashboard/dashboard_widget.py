import datetime
from typing import TYPE_CHECKING

import pandas as pd
from dateutil.relativedelta import relativedelta
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter
from PySide6.QtCore import QDate, QLocale, Qt
from PySide6.QtWidgets import (
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from brms.app.utils import pydate_to_qdate
from brms.app.views.styler import BRMSStyler

_locale = QLocale()

if TYPE_CHECKING:
    from matplotlib.lines import Line2D


def value_formatter(values: list[float]) -> FuncFormatter:
    """Return a FuncFormatter for formatting dollar values."""
    max_value = max(values, default=0)
    if max_value >= 1_000_000:
        return FuncFormatter(lambda x, _: _locale.toCurrencyString(x / 1_000_000) + "M")
    if max_value >= 1_000:
        return FuncFormatter(lambda x, _: _locale.toCurrencyString(x / 1_000) + "K")
    return FuncFormatter(lambda x, _: _locale.toCurrencyString(x))


def ratio_formatter() -> FuncFormatter:
    """Return a FuncFormatter for formatting ratios as percentages."""
    return FuncFormatter(lambda x, _: f"{x * 100:.2f}%")


class PlotWidget(QWidget):
    def __init__(
        self,
        title: str,
        line_titles: list[str],
        line_colors: list[str],
        *,
        use_ratio_formatter: bool = False,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.styler = BRMSStyler.instance()
        self.start_date: datetime.date = datetime.date.today() - relativedelta(years=1)
        self.end_date: datetime.date = datetime.date.today()
        self.dates: list[datetime.date] = []
        self.use_ratio_formatter = use_ratio_formatter
        self.canvas = FigureCanvas(Figure(figsize=(5, 3), facecolor=self.styler.plot_background_color))
        self.ax = self.canvas.figure.add_subplot()
        self.ax.set_title(title)
        self.ax.grid(visible=True, linestyle="--", alpha=0.7)
        self.ax.tick_params(axis="both", which="major", labelsize=10)
        self.formatter = value_formatter([1_000_000]) if not use_ratio_formatter else ratio_formatter()
        self.ax.yaxis.set_major_formatter(self.formatter)
        self.lines: dict[str, Line2D] = {}
        for i, line_title in enumerate(line_titles):
            (line2d,) = self.ax.plot([], [], color=line_colors[i], label=line_title)
            self.lines[line_title] = line2d
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.canvas)
        # Signals
        self.styler.style_changed.connect(self.update_plot_style)

    def update_plot_style(self) -> None:
        """Update an existing Matplotlib figure when the style changes."""
        if self.styler.use_custom_style:
            self.canvas.figure.patch.set_facecolor(self.styler.plot_background_color)  # Update figure background
        else:
            self.canvas.figure.patch.set_facecolor("white")  # Default background
        self.canvas.figure.canvas.draw_idle()  # Redraw canvas

    def update_plot(
        self,
        start_date: datetime.date | None,
        end_date: datetime.date | None,
        dates: list[datetime.date],
        data: dict[str, list[float]],
    ) -> None:
        if not dates or start_date is None or end_date is None:
            return
        self.ax.set_xlim(pd.Timestamp(start_date), pd.Timestamp(end_date))
        for line_title, values in data.items():
            if line2d := self.lines.get(line_title):
                line2d.set_data(dates, values)
                if not self.use_ratio_formatter:
                    self.formatter = value_formatter(values)
            # Recalculate limits and autoscale view
            self.ax.relim()
            self.ax.autoscale_view()
        self.ax.yaxis.set_major_formatter(self.formatter)
        if dates:
            self.ax.legend(fontsize=9, loc="lower right")
        self.canvas.draw_idle()


class BRMSDashboard(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)

        # Simulation statistics panel
        self.stats_group = QGroupBox("General")
        stats_layout = QFormLayout()
        stats_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Simulation
        simulation_label = QLabel("Simulation")
        font = simulation_label.font()
        font.setBold(True)
        simulation_label.setFont(font)
        stats_layout.addRow(simulation_label)
        self.simulation_date_label = QLabel("Current Date:")
        self.simulation_date_value = QLabel(QDate.currentDate().toString(Qt.DateFormat.ISODate))
        stats_layout.addRow(self.simulation_date_label, self.simulation_date_value)
        self.simulation_speed_label = QLabel("Simulation Speed:")
        self.simulation_speed_value = QLabel("1x")
        stats_layout.addRow(self.simulation_speed_label, self.simulation_speed_value)
        self.simulation_start_date_label = QLabel("Simulation Start Date:")
        self.simulation_start_date_value = QLabel(QDate.currentDate().toString(Qt.DateFormat.ISODate))
        stats_layout.addRow(self.simulation_start_date_label, self.simulation_start_date_value)
        self.simulation_end_date_label = QLabel("Simulation End Date:")
        self.simulation_end_date_value = QLabel(QDate.currentDate().toString(Qt.DateFormat.ISODate))
        stats_layout.addRow(self.simulation_end_date_label, self.simulation_end_date_value)
        self.simulation_progress_label = QLabel("Simulation Progress:")
        self.simulation_progress_value = QProgressBar()
        self.simulation_progress_value.setValue(0)
        stats_layout.addRow(self.simulation_progress_label, self.simulation_progress_value)

        # Bank
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.NoFrame)
        stats_layout.addRow(separator)
        bank_label = QLabel("Bank")
        font = bank_label.font()
        font.setBold(True)
        bank_label.setFont(font)
        stats_layout.addRow(bank_label)
        self.total_assets_label = QLabel("Total Assets:")
        self.total_assets_value = QLabel("0")
        stats_layout.addRow(self.total_assets_label, self.total_assets_value)
        self.total_liabilities_label = QLabel("Total Liabilities:")
        self.total_liabilities_value = QLabel("0")
        stats_layout.addRow(self.total_liabilities_label, self.total_liabilities_value)
        self.total_equity_label = QLabel("Total Equity:")
        self.total_equity_value = QLabel("0")
        stats_layout.addRow(self.total_equity_label, self.total_equity_value)

        # Capital Adequacy
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.NoFrame)
        stats_layout.addRow(separator)
        capital_ratio_label = QLabel("Capital Adequacy")
        font = capital_ratio_label.font()
        font.setBold(True)
        capital_ratio_label.setFont(font)
        stats_layout.addRow(capital_ratio_label)
        self.cet1_label = QLabel("CET1:")
        self.cet1_value = QLabel("0")
        stats_layout.addRow(self.cet1_label, self.cet1_value)
        self.cet1_ratio_label = QLabel("CET1 Ratio:")
        self.cet1_ratio_value = QLabel("0%")
        stats_layout.addRow(self.cet1_ratio_label, self.cet1_ratio_value)
        self.tier1_capital_ratio_label = QLabel("Tier 1 Capital Ratio:")
        self.tier1_capital_ratio_value = QLabel("0%")
        stats_layout.addRow(self.tier1_capital_ratio_label, self.tier1_capital_ratio_value)
        self.total_capital_ratio_label = QLabel("Total Capital Ratio:")
        self.total_capital_ratio_value = QLabel("0%")
        stats_layout.addRow(self.total_capital_ratio_label, self.total_capital_ratio_value)

        # Liquidity ratios
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.NoFrame)
        stats_layout.addRow(separator)
        liquidity_label = QLabel("Liquidity Ratios")
        font = liquidity_label.font()
        font.setBold(True)
        liquidity_label.setFont(font)
        stats_layout.addRow(liquidity_label)
        self.nsfr_label = QLabel("NSFR:")
        self.nsfr_value = QLabel("0%")
        stats_layout.addRow(self.nsfr_label, self.nsfr_value)
        self.lcr_label = QLabel("LCR:")
        self.lcr_value = QLabel("0%")
        stats_layout.addRow(self.lcr_label, self.lcr_value)

        # Set layout of statistics
        self.stats_group.setLayout(stats_layout)

        # Plot display area
        self.plot_splitter = QSplitter()
        self.plot_splitter.setOrientation(Qt.Orientation.Vertical)
        self.assets_liabilities_plot = PlotWidget(
            title="Total Assets and Liabilities",
            line_titles=["Total Assets", "Total Liabilities"],
            line_colors=["blue", "red"],
            use_ratio_formatter=False,
        )
        self.equity_plot = PlotWidget(
            title="Total Shareholders' Equity",
            line_titles=["Total Equity"],
            line_colors=["blue"],
            use_ratio_formatter=False,
        )
        self.capital_ratio_plot = PlotWidget(
            title="Capital Ratio",
            line_titles=["CET1 Ratio"],
            line_colors=["blue"],
            use_ratio_formatter=True,
        )
        self.plot_splitter.addWidget(self.assets_liabilities_plot)
        self.plot_splitter.addWidget(self.equity_plot)
        self.plot_splitter.addWidget(self.capital_ratio_plot)

        # Main layout as QSplitter
        main_splitter = QSplitter()
        main_splitter.setOrientation(Qt.Orientation.Horizontal)
        main_splitter.addWidget(self.stats_group)
        main_splitter.addWidget(self.plot_splitter)
        # Set relative sizes of statistics panel and display area
        main_splitter.setStretchFactor(1, 5)

        main_layout = QHBoxLayout()
        main_layout.addWidget(main_splitter)
        self.setLayout(main_layout)

    def update_simulation_date(self, date: datetime.date) -> None:
        """Update the current simulation date."""
        qdate = pydate_to_qdate(date)
        self.simulation_date_value.setText(qdate.toString(Qt.DateFormat.ISODate))

    def update_simulation_start_date(self, start_date: datetime.date) -> None:
        """Update the simulation start date."""
        qdate = pydate_to_qdate(start_date)
        self.simulation_start_date_value.setText(qdate.toString(Qt.DateFormat.ISODate))

    def update_simulation_end_date(self, end_date: datetime.date) -> None:
        """Update the simulation end date."""
        qdate = pydate_to_qdate(end_date)
        self.simulation_end_date_value.setText(qdate.toString(Qt.DateFormat.ISODate))

    def update_simulation_speed(self, speed: str) -> None:
        """Update the simulation speed."""
        self.simulation_speed_value.setText(speed)

    def update_simulation_progress(self, progress: int) -> None:
        """Update the simulation progress."""
        self.simulation_progress_value.setValue(progress)

    def update_bank_financials(self, data: dict) -> None:
        """Update the bank's financials from balance-sheet data dict.

        Parameters
        ----------
        data:
            Dict with keys ``total_assets``, ``total_liabilities``, ``total_equity``,
            and optional ``cet1``, ``cet1_ratio``, ``tier1_capital_ratio``,
            ``total_capital_ratio``, ``nsfr``, ``lcr``.

        """
        total_assets = data.get("total_assets", 0.0)
        total_liabilities = data.get("total_liabilities", 0.0)
        total_equity = data.get("total_equity", 0.0)
        cet1 = data.get("cet1", 0.0)
        cet1_ratio = data.get("cet1_ratio", 0.0)
        tier1_capital_ratio = data.get("tier1_capital_ratio", 0.0)
        total_capital_ratio = data.get("total_capital_ratio", 0.0)
        nsfr = data.get("nsfr", 0.0)
        lcr = data.get("lcr", 0.0)

        self.total_assets_value.setText(_locale.toCurrencyString(total_assets))
        self.total_liabilities_value.setText(_locale.toCurrencyString(total_liabilities))
        self.total_equity_value.setText(_locale.toCurrencyString(total_equity))
        self.cet1_value.setText(_locale.toCurrencyString(cet1))
        self.cet1_ratio_value.setText(f"{cet1_ratio * 100:.2f}%")
        self.tier1_capital_ratio_value.setText(f"{tier1_capital_ratio * 100:.2f}%")
        self.total_capital_ratio_value.setText(f"{total_capital_ratio * 100:.2f}%")
        self.nsfr_value.setText(f"{nsfr * 100:.2f}%")
        self.lcr_value.setText(f"{lcr * 100:.2f}%")

    def update_assets_liabilities_plot(self, start, end, dates, asset_values, liability_values) -> None:
        """Update the assets plot with new data."""
        self.assets_liabilities_plot.update_plot(
            start, end, dates, {"Total Assets": asset_values, "Total Liabilities": liability_values},
        )

    def update_equity_plot(self, start, end, dates, equity_values) -> None:
        """Update the equity plot with new data."""
        self.equity_plot.update_plot(start, end, dates, {"Total Equity": equity_values})

    def update_capital_ratio_plot(self, start, end, dates, values) -> None:
        """Update the equity plot with new data."""
        self.capital_ratio_plot.update_plot(start, end, dates, {"CET1 Ratio": values})
