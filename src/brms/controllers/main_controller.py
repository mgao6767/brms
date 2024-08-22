from brms.controllers import BankingBookController, TradingBookController
from brms.models.bank_model import BankModel
from brms.views.main_window import MainWindow


class MainController:

    def __init__(self, model: BankModel, view: MainWindow):
        self.model = model
        self.view = view

        # book models
        self.banking_book = self.model.banking_book
        self.trading_book = self.model.trading_book

        # book view/widget
        self.banking_book_widget = self.view.bank_books_widget.bank_banking_book_widget
        self.trading_book_widget = self.view.bank_books_widget.bank_trading_book_widget

        self.banking_book_controller = BankingBookController(
            self.banking_book, self.banking_book_widget
        )

        self.trading_book_controller = TradingBookController(
            self.trading_book, self.trading_book_widget
        )

        self.connect_signals_slots()
        self.post_init()

    def connect_signals_slots(self):

        self.view.next_action.triggered.connect(self.on_next_simulation)
        self.view.start_action.triggered.connect(self.on_start_simulation)
        self.view.pause_action.triggered.connect(self.on_pause_simulation)
        self.view.stop_action.triggered.connect(self.on_stop_simulation)

    def post_init(self):
        # Load yield data from resources
        try:
            yields = ":/data/par_yields.csv"
            self.view.yield_curve_ctrl.load_yield_data_from_qrc(yields)
        except FileNotFoundError as err:
            self.view.statusBar.showMessage("Failed to load yield data.")
            print(err)

    # ====== Simulation ========================================================
    def on_next_simulation(self):
        self.view.statusBar.showMessage("Simulation moved to next period.")

    def on_start_simulation(self):
        self.view.statusBar.showMessage("Simulation started.")
        self.view.next_action.setDisabled(True)
        self.view.start_action.setDisabled(True)
        self.view.pause_action.setEnabled(True)
        self.view.stop_action.setEnabled(True)

    def on_pause_simulation(self):
        self.view.statusBar.showMessage("Simulation paused.")
        self.view.next_action.setEnabled(True)
        self.view.start_action.setEnabled(True)
        self.view.pause_action.setDisabled(True)
        self.view.stop_action.setDisabled(True)

    def on_stop_simulation(self):
        self.view.statusBar.showMessage("Simulation stopped.")
        self.view.next_action.setDisabled(True)
        self.view.start_action.setDisabled(True)
        self.view.pause_action.setDisabled(True)
        self.view.stop_action.setDisabled(True)
