from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication, QStyleFactory


class BRMSStyler(QObject):
    """Singleton class to manage application-wide styles dynamically."""

    style_changed = Signal()  # Signal to notify UI when the style changes
    _instance = None

    def __init__(self):
        """Ensure QObject is initialized only once."""
        if BRMSStyler._instance is not None:
            return  # Prevent reinitialization
        super().__init__()  # Properly initialize QObject
        BRMSStyler._instance = self  # Store the instance
        self.use_custom_style = True
        # Define both custom styles and the default Fusion style
        self.Color_Red = "#A6192E"
        self.Color_Charcoal = "#373A36"
        self.Color_Sand_Light = "#EDEBE5"
        self.Color_Purple = "#80225F"
        self.Color_Deep_Red = "#76232F"
        self.Color_Bright_Red = "#D6001C"
        self.Color_Magenta = "#C6007E"
        self.Color_Success = "#009174"
        self.Color_Alert = "#BC4700"
        self.Color_Information = "#415364"
        self.Color_Sand = "#D6D2C4"
        self.Color_Dark_Purple = "#6F1D46"
        self.darker_sand = "#C0BEB0"  # Slightly darker than Color_Sand
        self.plot_background_color = "white"

    @classmethod
    def instance(cls):
        """Retrieve the singleton instance."""
        if cls._instance is None:
            cls._instance = BRMSStyler()
        return cls._instance

    def get_stylesheet(self):
        """Return the global stylesheet when custom style is active."""
        app_style = f"""
        QWidget {{
            background-color: {self.Color_Sand_Light};
            color: {self.Color_Charcoal};
        }}
        QDockWidget::title {{
            background-color: {self.Color_Sand};
            padding-top: 1px;
            padding-bottom: 1px;
            color: {self.Color_Sand_Light};
        }}
        QTabBar::tab {{
            background: {self.Color_Sand};
            color: {self.Color_Charcoal};
            border-bottom: 1px solid {self.Color_Sand_Light};
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
            min-width: 12ex;
            padding: 5px;
            padding-left: 10px;
            padding-right: 10px;
            margin-top: 5px;
            margin-right: 1px;
        }}
        QTabBar::tab::bottom {{
            background: {self.Color_Sand};
            color: {self.Color_Charcoal};
            border-top: 1px solid {self.Color_Sand_Light};
            border-top-left-radius: 0px;
            border-top-right-radius: 0px;
            border-bottom-left-radius: 4px;
            border-bottom-right-radius: 4px;
            min-width: 12ex;
            padding: 5px;
            padding-left: 10px;
            padding-right: 10px;
            margin-top: 0px;
            margin-bottom: 5px;
            margin-right: 1px;
        }}
        QTabBar::tab:selected {{
            background: {self.Color_Deep_Red};
            color: {self.Color_Sand_Light};
        }}
        QTabBar::tab:hover {{
            background: {self.Color_Red};
            color: {self.Color_Sand_Light};
        }}
        QPushButton {{
            background-color: {self.Color_Information};
            color: {self.Color_Sand_Light};
            border-radius: 5px;
            padding: 5px;
        }}
        QPushButton:hover {{
            background-color: {self.Color_Purple};
        }}
        QPushButton:pressed {{
            background-color: {self.Color_Dark_Purple};
        }}
        QPushButton:disabled {{
            background-color: {self.Color_Sand};
            color: {self.Color_Charcoal};
        }}
        QMenuBar {{
            background-color: {self.Color_Charcoal};
            color: {self.Color_Sand_Light};
        }}
        QMenuBar::item {{
            background-color: {self.Color_Charcoal};
            color: {self.Color_Sand_Light};
            padding-left: 10px;
            padding-right: 10px;
            padding-top: 5px;
            padding-bottom: 5px;
        }}
        QMenuBar::item:selected {{
            background-color: {self.Color_Purple};
        }}
        QMenu {{
            background-color: {self.Color_Charcoal};
            color: {self.Color_Sand_Light};
        }}
        QMenu::item:selected {{
            background-color: {self.Color_Purple};
        }}
        QToolBar {{
            background-color: {self.Color_Sand_Light};
        }}
        QToolBar QWidget {{
            background-color: {self.Color_Sand_Light};
        }}
        QToolButton {{
            background-color: {self.Color_Sand};
        }}
        QToolButton:hover {{
            background-color: {self.Color_Red};
            color: {self.Color_Sand_Light};
        }}
        QHeaderView::section {{
            background-color: {self.Color_Sand};
            border: none;
            padding: 3px;
        }}
        QTableCornerButton::section {{
            background-color: {self.Color_Sand};
        }}
        QTreeView::item:selected {{
            background-color: {self.Color_Alert};
            color: {self.Color_Sand_Light};
        }}
        QTableView::item:selected {{
            background-color: {self.Color_Alert};
            color: {self.Color_Sand_Light};
        }}
        QLabel {{
            background-color: transparent;
        }}
        QRadioButton {{
            background-color: transparent;
        }}
        QRadioButton::indicator {{
            background-color: {self.Color_Sand};
            border-radius: 2px;
        }}
        QRadioButton::indicator:checked {{
            background-color: {self.Color_Deep_Red};
        }}
        QRadioButton::indicator:unchecked {{
            color: {self.Color_Bright_Red};
        }}
        QRadioButton::indicator:hover {{
            background-color: {self.Color_Red};
        }}
        QRadioButton::indicator:pressed {{
            background-color: {self.Color_Dark_Purple};
        }}
        QRadioButton::indicator:disabled {{
        }}
        QRadioButton::disabled {{
            color: gray;
        }}
        """

        return app_style

    def apply_mq_style(self) -> None:
        if isinstance(app := QApplication.instance(), QApplication):
            self.use_custom_style = True
            app.setStyle(QStyleFactory.create("Fusion"))
            app.setStyleSheet(self.get_stylesheet())
            self.plot_background_color = self.Color_Sand_Light
            self.style_changed.emit()  # Notify UI components

    def apply_fusion_style(self) -> None:
        if isinstance(app := QApplication.instance(), QApplication):
            self.use_custom_style = False
            app.setStyle(QStyleFactory.create("Fusion"))
            app.setStyleSheet("")  # Remove custom styles
            self.plot_background_color = "white"
            self.style_changed.emit()  # Notify UI components
