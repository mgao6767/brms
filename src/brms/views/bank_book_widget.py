from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGroupBox, QHBoxLayout, QWidget, QSplitter

from brms.views.tree_widget import BRMSTreeWidget


class BRMSBankBookWidget(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.assets_tree = BRMSTreeWidget(["Exposure (Long)", "Value"])
        self.liabilities_tree = BRMSTreeWidget(["Exposure (Short)", "Value"])

        # Control panel
        ctrl_panel = QSplitter()
        ctrl_panel.setOrientation(Qt.Orientation.Vertical)
        analysis_group = QGroupBox("Analysis")
        management_group = QGroupBox("Management")
        ctrl_panel.addWidget(analysis_group)
        ctrl_panel.addWidget(management_group)

        # Create a splitter to display the tree views side by side
        splitter = QSplitter()
        splitter.addWidget(self.assets_tree)
        splitter.addWidget(self.liabilities_tree)

        # Create a layout for the widget and add the splitter
        book_layout = QHBoxLayout()
        book_layout.addWidget(ctrl_panel)
        book_layout.addWidget(splitter)
        self.setLayout(book_layout)
