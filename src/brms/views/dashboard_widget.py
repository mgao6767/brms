import datetime

import pandas as pd
from dateutil.relativedelta import relativedelta
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter
from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
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

from brms.accounting.report import Report
from brms.accounting.statement_viewer import locale
from brms.utils import pydate_to_qdate
from brms.views.styler import BRMSStyler


class PlotWidget(QWidget):
    def __init__(self, title: str = "", series_title: str = "", parent=None) -> None:
        super().__init__(parent)
        self.styler = BRMSStyler.instance()
        self.title = title
        self.series_title = series_title
        self.start_date: datetime.date = datetime.date.today() - relativedelta(years=1)
        self.end_date: datetime.date = datetime.date.today()
        self.dates: list[datetime.date] = []
        self.values: list[float] = []
        self.show_grid = True

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.canvas = FigureCanvas(Figure(figsize=(5, 3), facecolor=self.styler.plot_background_color))
        layout.addWidget(self.canvas)
        self.ax = self.canvas.figure.add_subplot()
        self.ax.set_title(self.title)
        if self.show_grid:
            self.ax.grid(self.show_grid, linestyle="--", alpha=0.7)
        self.ax.tick_params(axis="both", which="major", labelsize=10)
        self.ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: locale.currency(x, grouping=True)))
        # Checkboxes
        checkbox_layout = QHBoxLayout()
        checkbox_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        # Add checkbox for controlling grid lines
        self.grid_checkbox = QCheckBox("Show Grid Lines", self)
        self.grid_checkbox.setChecked(True)  # Default to showing grid lines
        checkbox_layout.addWidget(self.grid_checkbox)
        layout.addLayout(checkbox_layout)
        # Data containers
        (self.line,) = self.ax.plot([], [], color="blue", label=self.series_title)
        (self.marker,) = self.ax.plot([], [], "r+")
        # Signals
        self.grid_checkbox.stateChanged.connect(self.on_grid_checkbox_state_changed)
        self.styler.style_changed.connect(self.update_plot_style)
        # Finalize
        self.on_grid_checkbox_state_changed()

    def update_plot_style(self):
        """Update an existing Matplotlib figure when the style changes."""
        if self.styler.use_custom_style:
            self.canvas.figure.patch.set_facecolor(self.styler.plot_background_color)  # Update figure background
        else:
            self.canvas.figure.patch.set_facecolor("white")  # Default background
        self.canvas.figure.canvas.draw_idle()  # Redraw canvas

    def on_grid_checkbox_state_changed(self) -> None:
        self.update_plot(
            self.start_date,
            self.end_date,
            self.dates,
            self.values,
            self.grid_checkbox.isChecked(),
        )

    def clear_plot(self) -> None:
        self.ax.clear()
        # self.ax2.clear()
        self.ax.set_title(self.title)
        self.canvas.draw()

    def update_plot(
        self,
        start_date: datetime.date,
        end_date: datetime.date,
        dates: list[datetime.date],
        values: list[float],
        show_grid: bool,
    ) -> None:
        self.start_date = start_date
        self.end_date = end_date
        self.dates = dates
        self.values = values
        self.show_grid = show_grid

        self.ax.set_xlim(pd.Timestamp(start_date), pd.Timestamp(end_date))
        if show_grid:
            # When line properties are provided, the grid will be enabled regardless.
            self.ax.grid(True, linestyle="--", alpha=0.7)
        else:
            self.ax.grid(False)

        if dates and values:
            self.line.set_data(dates, values)
            self.marker.set_data([dates[-1]], [values[-1]])
            # Recalculate limits and autoscale view
            self.ax.relim()
            self.ax.autoscale_view()

        if max(values, default=0) >= 1_000_000:
            formatter = FuncFormatter(lambda x, _: locale.currency(x / 1_000_000, grouping=True) + "M")
        elif max(values, default=0) >= 1_000:
            formatter = FuncFormatter(lambda x, _: locale.currency(x / 1_000, grouping=True) + "K")
        else:
            formatter = FuncFormatter(lambda x, _: locale.currency(x, grouping=True))
        self.ax.yaxis.set_major_formatter(formatter)

        if dates:
            self.ax.legend(fontsize=9, loc="lower right")

        self.canvas.draw_idle()

    def export_plot(self) -> None:
        options = QFileDialog.Options()
        plot_title = self.ax.get_title()
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            caption="Save Plot",
            dir=f"BRMS - {plot_title}",
            filter="PNG Files (*.png);;All Files (*)",
            options=options,
        )
        if file_path:
            self.canvas.figure.savefig(file_path)


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
        self.equity_plot = PlotWidget(title="Total Shareholders' Equity", series_title="Total Equity")
        self.assets_plot = PlotWidget(title="Total Assets", series_title="Total Assets")
        self.liabilities_plot = PlotWidget(title="Total Liabilities", series_title="Total Liabilities")
        self.plot_splitter.addWidget(self.assets_plot)
        self.plot_splitter.addWidget(self.liabilities_plot)
        self.plot_splitter.addWidget(self.equity_plot)

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

    def update_bank_financials(self, report: Report) -> None:
        """Update the bank's financials."""
        total_assets = report.get_total_assets()
        total_liabilities = report.get_total_liabilities()
        total_equity = report.get_total_equity()
        cet1 = report.get_cet1()
        cet1_ratio = report.get_cet1_ratio()
        tier1_capital_ratio = report.get_tier1_capital_ratio()
        total_capital_ratio = report.get_total_capital_ratio()
        nsfr = report.get_net_stable_funding_ratio()
        lcr = report.get_liquidity_coverage_ratio()

        self.total_assets_value.setText(locale.currency(total_assets, grouping=True))
        self.total_liabilities_value.setText(locale.currency(total_liabilities, grouping=True))
        self.total_equity_value.setText(locale.currency(total_equity, grouping=True))
        self.cet1_value.setText(locale.currency(cet1, grouping=True))
        self.cet1_ratio_value.setText(f"{cet1_ratio*100:.2f}%")
        self.tier1_capital_ratio_value.setText(f"{tier1_capital_ratio*100:.2f}%")
        self.total_capital_ratio_value.setText(f"{total_capital_ratio*100:.2f}%")
        self.nsfr_value.setText(f"{nsfr*100:.2f}%")
        self.lcr_value.setText(f"{lcr*100:.2f}%")

    def update_assets_plot(self, start, end, dates, assets_values) -> None:
        """Update the assets plot with new data."""
        self.assets_plot.update_plot(
            start,
            end,
            dates,
            assets_values,
            self.assets_plot.grid_checkbox.isChecked(),
        )

    def update_liabilities_plot(self, start, end, dates, liabilities_values) -> None:
        """Update the liabilities plot with new data."""
        self.liabilities_plot.update_plot(
            start,
            end,
            dates,
            liabilities_values,
            self.liabilities_plot.grid_checkbox.isChecked(),
        )

    def update_equity_plot(self, start, end, dates, equity_values) -> None:
        """Update the equity plot with new data."""
        self.equity_plot.update_plot(
            start,
            end,
            dates,
            equity_values,
            self.equity_plot.grid_checkbox.isChecked(),
        )
