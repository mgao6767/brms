import numpy as np
import qtawesome as qta
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QCloseEvent, QShowEvent
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QSplitter,
    QStyledItemDelegate,
    QTableView,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from brms.app.views.styler import BRMSStyler


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


class BRMSYieldCurveWidget(QWidget):
    visibility_changed = Signal()

    def __init__(self, parent):
        super().__init__(parent)
        self.is_visible = False
        self.setWindowTitle("Yield Curve")

        self.toolbar = QToolBar()
        self.toolbar.setMovable(False)
        self.toolbar.setFloatable(False)
        self.toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)

        self.save_action = QAction(qta.icon("mdi6.export"), "Export Plot", self)
        self.table_action = QAction(qta.icon("mdi6.table-of-contents"), "Show Table", self)
        self.figure_action = QAction(qta.icon("mdi6.chart-bell-curve-cumulative"), "Show Plot", self)
        self.all_view_action = QAction(qta.icon("mdi.chart-multiple"), "Show Both", self)

        self.table_action.setCheckable(True)
        self.figure_action.setCheckable(True)
        self.all_view_action.setCheckable(True)

        self.toolbar.addAction(self.table_action)
        self.toolbar.addAction(self.figure_action)
        self.toolbar.addAction(self.all_view_action)
        self.toolbar.addAction(self.save_action)

        self.table_view = QTableView()
        self.table_view.setHorizontalHeader(RightAlignHeaderView(Qt.Horizontal))
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_view.setSelectionBehavior(QTableView.SelectRows)
        self.table_view.setItemDelegate(YieldItemDelegate())

        self.plot_widget = PlotWidget(self)

        self.splitter = QSplitter()
        self.splitter.setOrientation(Qt.Orientation.Horizontal)
        self.splitter.addWidget(self.table_view)
        self.splitter.addWidget(self.plot_widget)

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.toolbar)
        main_layout.addWidget(self.splitter)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.setLayout(main_layout)

        self.all_view_action.triggered.connect(self.set_default_view)
        self.table_action.triggered.connect(self.set_table_view)
        self.figure_action.triggered.connect(self.set_figure_view)
        self.save_action.triggered.connect(self.plot_widget.export_plot)

        self.set_default_view()

    def set_model(self, model):
        self.table_view.setModel(model)

    def set_default_view(self):
        self.all_view_action.setChecked(True)
        self.figure_action.setChecked(False)
        self.table_action.setChecked(False)
        total_size = 1000  # Arbitrary total size
        table_view_size = int(total_size * 0.5)
        plot_widget_size = total_size - table_view_size
        self.splitter.setSizes([table_view_size, plot_widget_size])

    def set_table_view(self):
        self.table_action.setChecked(True)
        self.figure_action.setChecked(False)
        self.all_view_action.setChecked(False)
        self.splitter.setSizes([1, 0])

    def set_figure_view(self):
        self.figure_action.setChecked(True)
        self.table_action.setChecked(False)
        self.all_view_action.setChecked(False)
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
        self.styler = BRMSStyler.instance()
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.canvas = FigureCanvas(
            Figure(figsize=(5, 3), facecolor=self.styler.plot_background_color, constrained_layout=False),
        )
        self.layout.addWidget(self.canvas)
        self.ax = self.canvas.figure.add_subplot()
        self.styler.style_axes(self.ax, title="Yield Curve")
        # Checkboxes
        checkbox_layout = QHBoxLayout()
        checkbox_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        # Add checkbox for controlling y-axis rescaling
        self.rescale_checkbox = QCheckBox("Rescale Y-Axis", self)
        self.rescale_checkbox.setChecked(False)  # Default to fixed Y-axis
        checkbox_layout.addWidget(self.rescale_checkbox)
        # Add checkbox for controlling grid lines
        self.grid_checkbox = QCheckBox("Show Grid Lines", self)
        self.grid_checkbox.setChecked(True)  # Default to showing grid lines
        checkbox_layout.addWidget(self.grid_checkbox)
        self.layout.addLayout(checkbox_layout)
        # Signals
        self.styler.style_changed.connect(self.update_plot_style)

    def update_plot_style(self):
        """Update figure and axes colors to match the theme."""
        self.styler.style_figure(self.canvas.figure)
        self.styler.style_axes(self.ax)
        self.canvas.draw_idle()

    def clear_plot(self):
        self.ax.clear()
        self.styler.style_axes(self.ax, title="Yield Curve")
        self.canvas.draw()

    def update_plot(self, maturities, yields, maturities_z, zero_rates, title, rescale_y, show_grid):
        self.ax.clear()
        self.ax.plot(maturities, yields, marker="o", color=self.styler.chart_palette[0], label="Treasury Par Yields")
        self.ax.plot(maturities_z, zero_rates, color=self.styler.chart_palette[1], label="Interpolated Zero Rates")
        self.ax.set_ylabel("Yield (%)", fontsize=9)
        # Rescale y-axis if checkbox is checked
        if rescale_y:
            self.ax.set_ybound(0, np.max(yields) * 1.1)
        else:
            self.ax.set_ybound(0.0, 10.0)
        self.styler.style_axes(self.ax, title=title)
        self.ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:.2f}"))
        self.styler.style_legend(self.ax)
        self.canvas.draw()

    def export_plot(self):
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


if __name__ == "__main__":
    import sys

    from PySide6.QtWidgets import QApplication, QMainWindow

    class MainWindow(QMainWindow):
        """MainWindow class for testing."""

        def __init__(self) -> None:
            """Initialize the MainWindow."""
            super().__init__()
            self.setWindowTitle("BRMS Inspector Widget Example")
            w = BRMSYieldCurveWidget(None)
            self.setCentralWidget(w)

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
