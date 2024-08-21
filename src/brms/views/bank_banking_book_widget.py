from PySide6.QtWidgets import QWidget

from brms.views.base import BankBookWidget

class BankBankingBookWidget(BankBookWidget):

    def __init__(self, parent: QWidget | None = ...) -> None:
        super().__init__(parent, book_name="Banking Book")
