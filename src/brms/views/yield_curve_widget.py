import numpy as np
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter
from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QAction, QCloseEvent, QIcon, QShowEvent
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QStyledItemDelegate,
    QTableView,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from brms.views.base import BRMSSplitter, BRMSWidget


class RightAlignHeaderView(QHeaderView):
    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        self.setDefaultAlignment(Qt.AlignRight | Qt.AlignVCenter)


class YieldItemDelegate(QStyledItemDelegate):
    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        option.displayAlignment = Qt.AlignRight | Qt.AlignVCenter

    def displayText(self, value, locale):
        try:
            return locale.toString(value, "f", 2)
        except ValueError:
            return value


class YieldCurveWidget(BRMSWidget):

    visibility_changed = Signal()

    def __init__(self, parent):
        super().__init__(parent)
        self._single_view_size = (700, 500)
        self._all_views_size = (1400, 500)
        self.is_visible = False
        self.setWindowTitle("Yield Curve")
        self.setGeometry(100, 100, *self._single_view_size)
        self.setMinimumSize(*self._single_view_size)

        self.toolbar = QToolBar()
        self.toolbar.setMovable(False)
        self.toolbar.setFloatable(False)
        self.toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.toolbar.setIconSize(QSize(32, 32))
        self.toolbar.setMaximumHeight(32)

        # fmt: off
        save_action = QAction(QIcon(":/icons/export.png"), "Export Plot", self)
        table_action = QAction(QIcon(":/icons/spreadsheet.png"), "Show Table", self)
        figure_action = QAction(QIcon(":/icons/line-chart-axis.png"), "Show Plot", self)
        all_view_action = QAction(QIcon(":/icons/table-and-graph.png"), "Show Both", self)
        # fmt: on

        self.toolbar.addAction(table_action)
        self.toolbar.addAction(figure_action)
        self.toolbar.addAction(all_view_action)
        self.toolbar.addAction(save_action)

        self.table_view = QTableView()
        self.table_view.setHorizontalHeader(RightAlignHeaderView(Qt.Horizontal))
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_view.setSelectionBehavior(QTableView.SelectRows)
        self.table_view.setItemDelegate(YieldItemDelegate())

        self.plot_widget = PlotWidget(self)

        self.splitter = BRMSSplitter()
        self.splitter.addWidget(self.table_view)
        self.splitter.addWidget(self.plot_widget)

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.toolbar)
        main_layout.addWidget(self.splitter)
        self.setLayout(main_layout)

        self.splitter.setContentsMargins(10, 10, 10, 10)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        all_view_action.triggered.connect(self.set_default_view)
        table_action.triggered.connect(self.set_table_view)
        figure_action.triggered.connect(self.set_figure_view)
        save_action.triggered.connect(self.plot_widget.export_plot)

        self.set_figure_view()
        self.center_window()

    def set_model(self, model):
        self.table_view.setModel(model)

    def set_default_view(self):
        self.resize(*self._all_views_size)
        total_size = 1000  # Arbitrary total size
        table_view_size = int(total_size * 0.5)
        plot_widget_size = total_size - table_view_size
        self.splitter.setSizes([table_view_size, plot_widget_size])

    def set_table_view(self):
        self.resize(*self._single_view_size)
        self.splitter.setSizes([1, 0])

    def set_figure_view(self):
        self.resize(*self._single_view_size)
        self.splitter.setSizes([0, 1])

    def showEvent(self, event: QShowEvent):
        self.is_visible = True
        self.visibility_changed.emit()
        super().showEvent(event)

    def closeEvent(self, event: QCloseEvent):
        self.is_visible = False
        self.visibility_changed.emit()
        super().closeEvent(event)


class PlotWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.canvas = FigureCanvas(Figure(figsize=(5, 3)))
        self.layout.addWidget(self.canvas)
        self.ax = self.canvas.figure.add_subplot(111)
        self.ax.set_title("Yield Curve", fontsize=11)
        # Checkboxes
        checkbox_layout = QHBoxLayout()
        checkbox_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        # Add checkbox for controlling y-axis rescaling
        self.rescale_checkbox = QCheckBox("Rescale Y-Axis", self)
        self.rescale_checkbox.setChecked(True)  # Default to rescaling
        checkbox_layout.addWidget(self.rescale_checkbox)
        # Add checkbox for controlling grid lines
        self.grid_checkbox = QCheckBox("Show Grid Lines", self)
        self.grid_checkbox.setChecked(True)  # Default to showing grid lines
        checkbox_layout.addWidget(self.grid_checkbox)
        # Add button for exporting plot to PNG
        # self.export_button = QPushButton("Export to PNG", self)
        # self.export_button.clicked.connect(self.export_plot)
        # checkbox_layout.addWidget(self.export_button)
        self.layout.addLayout(checkbox_layout)

    def clear_plot(self):
        self.ax.clear()
        self.ax.set_title("Yield Curve", fontsize=11)
        self.canvas.draw()

    def update_plot(
        self, maturities, yields, maturities_z, zero_rates, title, rescale_y, show_grid
    ):
        self.ax.clear()
        self.ax.plot(
            maturities, yields, marker="o", color="blue", label="Treasury Par Yields"
        )
        self.ax.plot(
            maturities_z, zero_rates, color="crimson", label="Interpolated Zero Rates"
        )
        self.ax.set_ylabel("Yield (%)", fontsize=11)
        # Rescale y-axis if checkbox is checked
        if rescale_y:
            self.ax.set_ybound(0, np.max(yields) * 1.1)
        else:
            self.ax.set_ybound(0.0, 10.0)
        self.ax.set_title(title, fontsize=11)
        if show_grid:
            self.ax.grid(True, linestyle="--", alpha=0.7)
        self.ax.tick_params(axis="both", which="major", labelsize=10)
        self.ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:.2f}"))
        self.ax.legend(fontsize=9, loc="lower right")
        self.canvas.draw()

    def export_plot(self):
        options = QFileDialog.Options()
        plot_title = self.ax.get_title()
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Plot",
            f"BRMS - {plot_title}",
            "PNG Files (*.png);;All Files (*)",
            options=options,
        )
        if file_path:
            self.canvas.figure.savefig(file_path)
