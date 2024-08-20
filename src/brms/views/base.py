from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QDoubleSpinBox, QMessageBox, QWidget


class CustomDoubleSpinBox(QDoubleSpinBox):

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

    def textFromValue(self, value):
        return self.locale().toString(value, "f", 2)


class BaseCalculatorWidget(QWidget):
    def __init__(self, parent=None, name="Calculator", size=(600, 560)):
        super().__init__(parent, Qt.WindowType.Dialog)
        self.setWindowTitle(name)
        self.setGeometry(100, 100, *size)
        self.center_window()

    def center_window(self):
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        window_geometry = self.frameGeometry()
        window_geometry.moveCenter(screen_geometry.center())
        self.move(window_geometry.topLeft())

    def show_warning(self, message: str = "Error"):
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle("Warning")
        msg_box.setText(message)
        msg_box.setInformativeText("Please check input parameters.")
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec()
