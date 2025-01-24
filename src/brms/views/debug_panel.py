from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton


class DebugPanel(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent, Qt.WindowType.Window)
        self.resize(300, 300)
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.btn_init = QPushButton("Init Default Simulation")
        self.btn_buy_htm_security = QPushButton("Buy HTM security")

        # Add buttons to layout
        layout.addWidget(self.btn_init)
        layout.addWidget(self.btn_buy_htm_security)

        self.setLayout(layout)
        self.setWindowTitle("Debug Panel")
