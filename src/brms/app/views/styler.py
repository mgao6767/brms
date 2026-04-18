"""Application-wide dark theme using BRMS design tokens."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication, QStyleFactory

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure


class BRMSStyler(QObject):
    """Singleton that manages the application-wide dark theme."""

    style_changed = Signal()
    tick_colors_changed = Signal(bool)
    _instance = None

    def __init__(self) -> None:
        """Initialize design tokens."""
        if BRMSStyler._instance is not None:
            return
        super().__init__()
        BRMSStyler._instance = self
        self.use_custom_style = True
        self.show_tick_colors = True

        # --- Surfaces ---
        self.background = "#0B0F14"
        self.layer_01 = "#11161D"
        self.layer_02 = "#161C24"
        self.layer_hover = "#1B2330"
        self.layer_selected = "#1E2E45"
        self.layer_input = "#0F141B"
        self.layer_overlay = "#151B23"
        self.row_alternate = "#10151C"

        # --- Text ---
        self.text_primary = "#E6EDF3"
        self.text_secondary = "#A8B3C2"
        self.text_muted = "#7D8896"
        self.text_on_color = "#F8FAFC"

        # --- Interactive ---
        self.interactive = "#3B82F6"
        self.interactive_hover = "#60A5FA"
        self.interactive_active = "#2563EB"
        self.highlight = "#1E2E45"

        # --- Border ---
        self.border_subtle = "#202A36"
        self.border_strong = "#304055"

        # --- Semantic ---
        self.support_success = "#22C55E"
        self.support_error = "#EF4444"
        self.support_warning = "#F59E0B"
        self.support_info = "#22D3EE"

        # --- Chart ---
        self.chart_blue = "#3B82F6"
        self.chart_red = "#EF4444"
        self.chart_green = "#22C55E"
        self.chart_amber = "#F59E0B"
        self.chart_purple = "#A78BFA"
        self.chart_cyan = "#22D3EE"
        self.chart_pink = "#F472B6"
        self.chart_sky = "#60A5FA"
        self.chart_emerald = "#10B981"
        self.chart_emerald_light = "#6EE7B7"
        self.chart_palette = [
            self.chart_blue, self.chart_red, self.chart_green, self.chart_amber,
            self.chart_purple, self.chart_cyan, self.chart_pink, self.chart_sky,
            self.chart_emerald, self.chart_emerald_light,
        ]
        self.chart_grid = "#3A4A5E"

        # --- Plot ---
        self.plot_background_color = "#11161D"

    @classmethod
    def instance(cls) -> BRMSStyler:
        """Retrieve the singleton instance."""
        if cls._instance is None:
            cls._instance = BRMSStyler()
        return cls._instance

    def set_tick_colors(self, enabled: bool) -> None:  # noqa: FBT001
        """Toggle green/red value-change coloring across statements, bank book, and dashboard."""
        if self.show_tick_colors != enabled:
            self.show_tick_colors = enabled
            self.tick_colors_changed.emit(enabled)

    def style_figure(self, fig: Figure) -> None:
        """Apply dark theme to a matplotlib Figure."""
        fig.patch.set_facecolor(self.plot_background_color)

    def style_axes(self, ax: Axes, title: str = "", *, show_grid: bool = True) -> None:
        """Apply dark theme to a matplotlib Axes (call at init and on style_changed)."""
        ax.set_facecolor(self.plot_background_color)
        if title:
            ax.set_title(title, fontsize=9, fontweight="semibold", loc="left", pad=4, color=self.text_primary)
        else:
            ax.title.set_color(self.text_primary)
        ax.tick_params(axis="both", which="major", labelsize=8, colors=self.text_muted)
        ax.xaxis.label.set_color(self.text_secondary)
        ax.yaxis.label.set_color(self.text_secondary)
        for spine in ax.spines.values():
            spine.set_edgecolor(self.border_subtle)
        if show_grid:
            ax.grid(visible=True, linestyle="--", alpha=0.4, color=self.chart_grid, linewidth=0.6)
        else:
            ax.grid(visible=False)

    def style_legend(self, ax: Axes, **kwargs: object) -> object:
        """Create a dark-themed legend on the given axes. Returns the Legend object."""
        defaults = {"fontsize": 8, "loc": "lower right", "framealpha": 0, "labelcolor": self.text_secondary}
        defaults.update(kwargs)
        return ax.legend(**defaults)

    def get_stylesheet(self) -> str:
        """Return the global dark-theme stylesheet."""
        return f"""
        /* ---- Base ---- */
        QWidget {{
            background-color: {self.background};
            color: {self.text_primary};
            font-family: "IBM Plex Sans", "Helvetica Neue", Arial, sans-serif;
            font-size: 12px;
        }}

        QPlainTextEdit, QTextEdit[role="code"], QLabel[role="mono"] {{
            font-family: "IBM Plex Mono", Menlo, Courier, monospace;
        }}

        QLabel {{
            background-color: transparent;
        }}

        /* ---- Main Window ---- */
        QMainWindow {{
            background-color: {self.background};
        }}

        /* ---- Dock Widgets ---- */
        QDockWidget::title {{
            background-color: {self.layer_02};
            color: {self.text_secondary};
            padding: 6px 8px;
            font-size: 12px;
            font-weight: 600;
        }}

        /* ---- Tabs ---- */
        QTabBar::tab {{
            background: {self.layer_02};
            color: {self.text_secondary};
            border: none;
            border-bottom: 2px solid transparent;
            border-radius: 0px;
            min-width: 10ex;
            padding: 6px 12px;
            margin-right: 2px;
            font-size: 12px;
        }}
        QTabBar::tab:selected {{
            background: {self.layer_01};
            color: {self.text_primary};
            border-bottom: 2px solid {self.interactive};
        }}
        QTabBar::tab:hover {{
            background: {self.layer_hover};
            color: {self.text_primary};
        }}
        QTabBar::tab::bottom {{
            background: {self.layer_02};
            color: {self.text_secondary};
            border: none;
            border-top: 2px solid transparent;
            border-radius: 0px;
            min-width: 10ex;
            padding: 6px 12px;
            margin-right: 2px;
            font-size: 12px;
        }}
        QTabBar::tab::bottom:selected {{
            background: {self.layer_01};
            color: {self.text_primary};
            border-top: 2px solid {self.interactive};
        }}
        QTabBar::tab::bottom:hover {{
            background: {self.layer_hover};
            color: {self.text_primary};
        }}
        QTabWidget::pane {{
            background-color: {self.layer_01};
            border: none;
        }}

        /* ---- Buttons ---- */
        QPushButton {{
            background-color: {self.layer_02};
            color: {self.text_primary};
            border: 1px solid {self.border_subtle};
            border-radius: 4px;
            min-height: 24px;
            padding: 4px 10px;
            font-size: 12px;
        }}
        QPushButton:hover {{
            background-color: {self.layer_hover};
        }}
        QPushButton:pressed {{
            background-color: {self.layer_selected};
        }}
        QPushButton:disabled {{
            background-color: {self.layer_02};
            color: {self.text_muted};
            border-color: {self.border_subtle};
        }}
        QPushButton[variant="primary"] {{
            background-color: {self.interactive};
            color: {self.text_on_color};
            border: 1px solid {self.interactive};
        }}
        QPushButton[variant="primary"]:hover {{
            background-color: {self.interactive_hover};
        }}

        /* ---- MenuBar ---- */
        QMenuBar {{
            background-color: {self.layer_02};
            color: {self.text_secondary};
            font-size: 12px;
        }}
        QMenuBar::item {{
            background-color: transparent;
            color: {self.text_secondary};
            padding: 6px 10px;
        }}
        QMenuBar::item:selected {{
            background-color: {self.layer_hover};
            color: {self.text_primary};
        }}

        /* ---- Menu ---- */
        QMenu {{
            background-color: {self.layer_overlay};
            color: {self.text_primary};
            border: 1px solid {self.border_subtle};
            font-size: 12px;
        }}
        QMenu::item {{
            padding: 6px 24px 6px 12px;
        }}
        QMenu::item:selected {{
            background-color: {self.layer_hover};
        }}
        QMenu::separator {{
            height: 1px;
            background-color: {self.border_subtle};
            margin: 4px 8px;
        }}

        /* ---- ToolBar ---- */
        QToolBar {{
            background-color: {self.layer_02};
            border-bottom: 1px solid {self.border_subtle};
            spacing: 2px;
        }}
        QToolBar QWidget {{
            background-color: {self.layer_02};
        }}
        QToolButton {{
            background-color: transparent;
            border-radius: 4px;
            padding: 3px 6px;
            font-size: 12px;
        }}
        QToolButton:hover {{
            background-color: {self.layer_hover};
        }}
        QToolButton:checked {{
            background-color: {self.layer_selected};
            color: {self.interactive_hover};
        }}

        /* ---- Header / Table Corner ---- */
        QHeaderView::section {{
            background-color: {self.layer_02};
            color: {self.text_secondary};
            border: none;
            border-right: 1px solid {self.border_subtle};
            border-bottom: 1px solid {self.border_subtle};
            padding: 4px 8px;
            font-size: 11px;
            font-weight: 600;
        }}
        QTableCornerButton::section {{
            background-color: {self.layer_02};
            border: none;
        }}

        /* ---- Tree / Table ---- */
        QTreeView, QTableView, QTableWidget {{
            background-color: {self.layer_01};
            alternate-background-color: {self.row_alternate};
            gridline-color: {self.border_subtle};
            border: 1px solid {self.border_subtle};
            selection-background-color: {self.layer_selected};
            selection-color: {self.text_primary};
        }}
        QTreeView::item, QTableView::item {{
            padding: 2px 4px;
        }}
        QTreeView::item:selected, QTableView::item:selected {{
            background-color: {self.layer_selected};
            color: {self.text_primary};
        }}
        QTreeView::item:focus, QTableView::item:focus {{
            border-left: 3px solid {self.interactive};
        }}
        QTreeView::item:hover, QTableView::item:hover {{
            background-color: {self.layer_hover};
        }}

        /* ---- Inputs ---- */
        QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit {{
            background-color: {self.layer_input};
            color: {self.text_primary};
            border: 1px solid {self.border_subtle};
            border-radius: 4px;
            min-height: 24px;
            padding: 4px 8px;
            font-size: 12px;
        }}
        QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus {{
            border: 1px solid {self.interactive};
        }}

        /* ---- ComboBox dropdown ---- */
        QComboBox::drop-down {{
            border: none;
        }}
        QComboBox QAbstractItemView {{
            background-color: {self.layer_overlay};
            color: {self.text_primary};
            border: 1px solid {self.border_subtle};
            selection-background-color: {self.layer_hover};
        }}

        /* ---- GroupBox ---- */
        QGroupBox {{
            background-color: {self.layer_01};
            border: 1px solid {self.border_subtle};
            border-radius: 4px;
            margin-top: 12px;
            padding-top: 20px;
            font-size: 12px;
            font-weight: 600;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0px 8px;
            color: {self.text_secondary};
        }}

        /* ---- Radio / Checkbox ---- */
        QRadioButton, QCheckBox {{
            background-color: transparent;
            font-size: 12px;
            spacing: 6px;
        }}
        QRadioButton::indicator {{
            width: 14px;
            height: 14px;
            border: 2px solid {self.text_muted};
            border-radius: 8px;
            background-color: transparent;
        }}
        QRadioButton::indicator:checked {{
            background-color: {self.interactive};
            border-color: {self.interactive};
        }}
        QRadioButton::indicator:hover {{
            border-color: {self.interactive};
        }}
        QRadioButton::indicator:disabled {{
            border-color: {self.border_subtle};
        }}
        QRadioButton:disabled {{
            color: {self.text_muted};
        }}
        QCheckBox::indicator {{
            width: 14px;
            height: 14px;
            border: 2px solid {self.text_muted};
            border-radius: 2px;
            background-color: transparent;
        }}
        QCheckBox::indicator:checked {{
            background-color: {self.interactive};
            border-color: {self.interactive};
        }}
        QCheckBox::indicator:hover {{
            border-color: {self.interactive};
        }}

        /* ---- Progress Bar ---- */
        QProgressBar {{
            background-color: {self.layer_02};
            border: none;
            border-radius: 0px;
            text-align: center;
            color: {self.text_secondary};
            font-size: 10px;
        }}
        QProgressBar::chunk {{
            background-color: {self.interactive};
            border-radius: 0px;
        }}

        /* ---- Splitter ---- */
        QSplitter::handle {{
            background-color: {self.border_subtle};
            width: 1px;
            height: 1px;
        }}

        /* ---- Scroll Bars ---- */
        QScrollBar:vertical {{
            background: {self.background};
            width: 8px;
        }}
        QScrollBar::handle:vertical {{
            background: {self.border_subtle};
            min-height: 24px;
            border-radius: 4px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {self.border_strong};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
        QScrollBar:horizontal {{
            background: {self.background};
            height: 8px;
        }}
        QScrollBar::handle:horizontal {{
            background: {self.border_subtle};
            min-width: 24px;
            border-radius: 4px;
        }}
        QScrollBar::handle:horizontal:hover {{
            background: {self.border_strong};
        }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            width: 0px;
        }}

        /* ---- Status Bar ---- */
        QStatusBar {{
            background-color: {self.layer_02};
            color: {self.text_secondary};
            font-size: 11px;
        }}
        QStatusBar QLabel#statusSegment {{
            padding: 2px 10px;
            border-left: 1px solid {self.border_subtle};
        }}
        QStatusBar QLabel#statusSegmentFirst {{
            padding: 2px 10px;
        }}

        /* ---- Text Browser ---- */
        QTextBrowser {{
            background-color: {self.layer_01};
            color: {self.text_primary};
            border: 1px solid {self.border_subtle};
        }}

        /* ---- Frame separators ---- */
        QFrame[frameShape="4"], QFrame[frameShape="5"] {{
            color: {self.border_subtle};
        }}

        /* ---- Styled Panel (KPI cards, sim strip) ---- */
        QFrame[frameShape="6"] {{
            background-color: {self.layer_01};
            border: 1px solid {self.border_subtle};
        }}
        """

    def apply_style(self) -> None:
        """Apply the dark theme to the application."""
        if isinstance(app := QApplication.instance(), QApplication):
            self.use_custom_style = True
            app.setStyle(QStyleFactory.create("Fusion"))
            app.setStyleSheet(self.get_stylesheet())
            self.style_changed.emit()
