import datetime

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QFrame,
    QPushButton,
    QSplitter,
    QWidget,
    QProgressBar,
)

from brms.utils import pydate_to_qdate
from brms.accounting.statement_viewer import locale


class BRMSDashboard(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)

        # Simulation statistics panel
        self.stats_group = QGroupBox("General")
        stats_layout = QFormLayout()
        stats_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

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

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
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

        self.stats_group.setLayout(stats_layout)

        # Plot display area
        self.plot_splitter = QSplitter()
        self.plot_splitter.setOrientation(Qt.Orientation.Vertical)
        self.plot_splitter.addWidget(QLabel("Plot 1 Placeholder"))
        self.plot_splitter.addWidget(QLabel("Plot 2 Placeholder"))
        self.plot_splitter.addWidget(QLabel("Plot 3 Placeholder"))

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

    def update_bank_financials(self, total_assets: float, total_liabilities: float, total_equity: float) -> None:
        """Update the bank's financials."""
        self.total_assets_value.setText(locale.currency(total_assets, grouping=True))
        self.total_liabilities_value.setText(locale.currency(total_liabilities, grouping=True))
        self.total_equity_value.setText(locale.currency(total_equity, grouping=True))
