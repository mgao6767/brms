import sys

from PySide6.QtWidgets import QApplication

from brms.controllers.main_controller import MainController
from brms.models.bank_model import BankModel
from brms.views.main_window import MainWindow


class App(QApplication):

    def __init__(self, sys_argv):
        super(App, self).__init__(sys_argv)
        self.view = MainWindow()
        self.model = BankModel()
        self.controller = MainController(self.model, self.view)
        self.view.show()


def main():
    app = App(sys.argv)
    app.exec()


if __name__ == "__main__":
    main()
