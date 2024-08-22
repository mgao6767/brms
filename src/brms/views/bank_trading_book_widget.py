from PySide6.QtWidgets import QWidget

from brms.views.base import BankBookWidget


class BankTradingBookWidget(BankBookWidget):

    def __init__(self, parent: QWidget | None = ...) -> None:
        super().__init__(parent, book_name="Trading Book")
