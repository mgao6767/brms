from PySide6.QtCore import QObject


class BRMSController(QObject):

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)

    def reset(self):
        raise NotImplementedError
