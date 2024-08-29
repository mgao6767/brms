import sys

from PySide6.QtWidgets import QApplication

from brms.controllers.main_controller import MainController
from brms.models.scenario_model import ScenarioModel
from brms.views.main_window import MainWindow


class App(QApplication):

    def __init__(self, sys_argv):
        super(App, self).__init__(sys_argv)
        self.view = MainWindow()
        self.model = ScenarioModel()
        self.controller = MainController(self.model, self.view)
        self.view.show()
        self.view.show_load_scenario_messagebox()


def main():
    app = App(sys.argv)
    app.exec()


if __name__ == "__main__":
    main()
