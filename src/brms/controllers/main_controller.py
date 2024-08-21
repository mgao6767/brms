from brms.models.bank_model import BankModel
from brms.views.main_window import MainWindow


class MainController:

    def __init__(self, model: BankModel, view: MainWindow):
        self.model = model
        self.view = view