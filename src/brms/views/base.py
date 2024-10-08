from PySide6.QtCore import QAbstractItemModel, QModelIndex, Qt
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QApplication,
    QDoubleSpinBox,
    QMessageBox,
    QSplitter,
    QSplitterHandle,
    QStyledItemDelegate,
    QWidget,
)


class BRMSDoubleSpinBox(QDoubleSpinBox):

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

    def textFromValue(self, value):
        return self.locale().toString(value, "f", 2)


class BRMSSplitterHandle(QSplitterHandle):
    def __init__(self, orientation, parent):
        super().__init__(orientation, parent)
        self.default_color = "transparent"
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


class BRMSSplitter(QSplitter):
    def createHandle(self):
        return BRMSSplitterHandle(self.orientation(), self)


class BRMSWidget(QWidget):

    def __init__(
        self, parent: QWidget | None = ..., f: Qt.WindowType = Qt.WindowType.Window
    ) -> None:
        super().__init__(parent, f)

    def center_window(self):
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        window_geometry = self.frameGeometry()
        window_geometry.moveCenter(screen_geometry.center())
        self.move(window_geometry.topLeft())

    def show_warning(self, message="Error", informative_text=""):
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle("Warning")
        msg_box.setText(message)
        if len(informative_text):
            msg_box.setInformativeText(informative_text)
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec()


class TreeItem:
    def __init__(self, data, parent=None):
        self.parent_item = parent
        self.item_data = data
        self.child_items = []

    def append_child(self, item):
        self.child_items.append(item)

    def child(self, row):
        return self.child_items[row]

    def child_count(self):
        return len(self.child_items)

    def column_count(self):
        return len(self.item_data)

    def data(self, column):
        if column < 0 or column >= len(self.item_data):
            return None
        return self.item_data[column]

    def parent(self):
        return self.parent_item

    def row(self):
        if self.parent_item:
            return self.parent_item.child_items.index(self)
        return 0


class TreeModel(QAbstractItemModel):
    def __init__(self, headers, data, parent=None):
        super().__init__(parent)
        self.root_item = TreeItem(headers)
        self.setup_model_data(data, self.root_item)

    def columnCount(self, parent=QModelIndex()):
        if parent.isValid():
            return parent.internalPointer().column_count()
        return self.root_item.column_count()

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        item = index.internalPointer()
        if role == Qt.DisplayRole:
            return item.data(index.column())
        # Apply color to the value column
        if role == Qt.ForegroundRole and index.column() == 1:
            color = item.data(2)  # color string in the 3rd column
            return QBrush(QColor(color))
        return None

    def flags(self, index):
        if not index.isValid():
            return Qt.NoItemFlags
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.root_item.data(section)
        return None

    def index(self, row, column, parent=QModelIndex()):
        if not self.hasIndex(row, column, parent):
            return QModelIndex()
        if not parent.isValid():
            parent_item = self.root_item
        else:
            parent_item = parent.internalPointer()
        child_item = parent_item.child(row)
        if child_item:
            return self.createIndex(row, column, child_item)
        return QModelIndex()

    def parent(self, index):
        if not index.isValid():
            return QModelIndex()
        child_item = index.internalPointer()
        parent_item = child_item.parent()
        if parent_item == self.root_item:
            return QModelIndex()
        return self.createIndex(parent_item.row(), 0, parent_item)

    def rowCount(self, parent=QModelIndex()):
        if parent.column() > 0:
            return 0
        if not parent.isValid():
            parent_item = self.root_item
        else:
            parent_item = parent.internalPointer()
        return parent_item.child_count()

    def setup_model_data(self, data, parent):
        for item_data in data:
            item = TreeItem(item_data["data"], parent)
            parent.append_child(item)
            if "children" in item_data:
                self.setup_model_data(item_data["children"], item)


class NumberFormatDelegate(QStyledItemDelegate):
    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        option.displayAlignment = Qt.AlignRight | Qt.AlignVCenter

    def displayText(self, value, locale):
        try:
            return f"{value:,.2f}"
        except ValueError:
            return str(value)
