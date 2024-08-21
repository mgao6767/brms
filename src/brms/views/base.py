from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QDoubleSpinBox, QMessageBox, QWidget 
from PySide6.QtWidgets import QTreeView, QVBoxLayout, QSplitterHandle, QSplitter, QGroupBox

class CustomDoubleSpinBox(QDoubleSpinBox):

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

    def textFromValue(self, value):
        return self.locale().toString(value, "f", 2)

class CustomSplitterHandle(QSplitterHandle):
    def __init__(self, orientation, parent):
        super().__init__(orientation, parent)
        self.default_color = "none"
        self.hover_color = "lightblue"
        self.setStyleSheet(f"background-color: {self.default_color};")

    def enterEvent(self, event):
        # Change to hover color when the mouse enters the handle area
        self.setStyleSheet(f"background-color: {self.hover_color};")
        super().enterEvent(event)

    def leaveEvent(self, event):
        # Change back to default color when the mouse leaves the handle area
        self.setStyleSheet(f"background-color: {self.default_color};")
        super().leaveEvent(event)

class CustomSplitter(QSplitter):
    def createHandle(self):
        return CustomSplitterHandle(self.orientation(), self)

class CustomWidget(QWidget):

    def __init__(self, parent: QWidget | None = ..., f: Qt.WindowType = Qt.WindowType.Window) -> None:
        super().__init__(parent, f)

    def center_window(self):
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        window_geometry = self.frameGeometry()
        window_geometry.moveCenter(screen_geometry.center())
        self.move(window_geometry.topLeft())

class BaseCalculatorWidget(CustomWidget):
    def __init__(self, parent=None, name="Calculator", size=(600, 560)):
        super().__init__(parent, Qt.WindowType.Window)
        self.setWindowTitle(name)
        self.setGeometry(100, 100, *size)
        self.center_window()

    def show_warning(self, message: str = "Error"):
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle("Warning")
        msg_box.setText(message)
        msg_box.setInformativeText("Please check input parameters.")
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec()

class BankBookWidget(QWidget):
    def __init__(self, parent: QWidget | None = ..., book_name: str = "") -> None:
        super().__init__(parent)
        self.book_name = book_name

        group_box = QGroupBox(book_name)

        assets_tree_view = QTreeView()
        liabilities_tree_view = QTreeView()

        # Create a splitter to display the tree views side by side
        splitter = CustomSplitter()
        splitter.addWidget(assets_tree_view)
        splitter.addWidget(liabilities_tree_view)

        # Create a layout for the widget and add the splitter
        layout = QVBoxLayout()
        layout.addWidget(splitter)

        group_box.setLayout(layout)

        book_layout = QVBoxLayout()
        book_layout.addWidget(group_box)
        self.setLayout(book_layout)
