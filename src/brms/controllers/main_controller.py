import datetime

import QuantLib as ql
from PySide6.QtCore import QObject, QTimer

from brms.controllers import BankingBookController, TradingBookController
from brms.models.bank_model import BankModel
from brms.utils import pydate_to_qldate, qldate_to_pydate
from brms.views.main_window import MainWindow


class MainController(QObject):

    def __init__(self, model: BankModel, view: MainWindow):
        self.model = model
        self.view = view

        # Initialize the timer
        self.simulation_timer = QTimer()
        self.simulation_timer.setInterval(100)  # 0.1 seconds
        self.simulation_timer.timeout.connect(self.on_next_simulation)

        # Current date in the simulation
        self.dates_in_simulation = []
        self.current_date: ql.Date = ql.Date()

        # book models
        self.banking_book = self.model.banking_book
        self.trading_book = self.model.trading_book

        # book view/widget
        self.banking_book_widget = self.view.bank_books_widget.bank_banking_book_widget
        self.trading_book_widget = self.view.bank_books_widget.bank_trading_book_widget

        # fmt: off
        self.banking_book_controller = BankingBookController(self.banking_book, self.banking_book_widget)
        self.trading_book_controller = TradingBookController(self.trading_book, self.trading_book_widget)

        self.connect_signals_slots()
        self.post_init()

        self._test_setup()

    def connect_signals_slots(self):

        self.view.next_action.triggered.connect(self.on_next_simulation)
        self.view.start_action.triggered.connect(self.on_start_simulation)
        self.view.pause_action.triggered.connect(self.on_pause_simulation)
        self.view.stop_action.triggered.connect(self.on_stop_simulation)

    def _test_setup(self):
        from brms.models.instruments import InstrumentFactory

        cash = InstrumentFactory.create_cash(1_000_000_000.0)
        self.banking_book_controller.add_asset(cash)
        self.banking_book_controller.add_asset(cash)

        self.view.loan_calculator.calculate_button.clicked.connect(self._test_add_loan)

    def _test_add_loan(self):

        from brms.models.instruments import InstrumentFactory

        _, params = self.view.loan_calculator_ctrl.build_loan()

        loan = InstrumentFactory.create_fixed_rate_mortgage(*params[4:])
        self.banking_book_controller.add_asset(loan)

    def post_init(self):
        # Load yield data from resources
        try:
            yields = ":/data/par_yields.csv"
            self.view.yield_curve_ctrl.load_yield_data_from_qrc(yields)
        except FileNotFoundError as err:
            self.view.statusBar.showMessage("Failed to load yield data.")
            print(err)
            return

        # The dates of yields become dates in the simulation
        self.dates_in_simulation = [
            pydate_to_qldate(date)
            for date in self.view.yield_curve_ctrl.get_all_dates()
        ]
        self.view.yield_curve_ctrl.set_current_selection(0, 0)
        current_date = self.view.yield_curve_ctrl.get_date_from_selection()
        self.set_current_simulation_date(current_date)

    # ====== Simulation ========================================================
    def on_next_simulation(self):
        self.view.statusBar.showMessage("Simulation moved to next period.")
        idx = self.dates_in_simulation.index(self.current_date)
        if idx >= len(self.dates_in_simulation) - 1:
            self.on_stop_simulation()
            return
        self.view.yield_curve_ctrl.set_current_selection(idx + 1, 0)
        next_date = self.dates_in_simulation[idx + 1]
        self.set_current_simulation_date(next_date)

    def on_start_simulation(self):
        self.view.statusBar.showMessage("Simulation started.")
        self.view.next_action.setDisabled(True)
        self.view.start_action.setDisabled(True)
        self.view.pause_action.setEnabled(True)
        self.view.stop_action.setEnabled(True)
        # Start the timer with an interval of 100 milliseconds (0.1 second)
        self.simulation_timer.start()

    def on_pause_simulation(self):
        self.view.statusBar.showMessage("Simulation paused.")
        self.view.next_action.setEnabled(True)
        self.view.start_action.setEnabled(True)
        self.view.pause_action.setDisabled(True)
        self.view.stop_action.setDisabled(True)
        # Stop the timer
        self.simulation_timer.stop()

    def on_stop_simulation(self):
        self.view.statusBar.showMessage("Simulation stopped.")
        self.view.next_action.setDisabled(True)
        self.view.start_action.setDisabled(True)
        self.view.pause_action.setDisabled(True)
        self.view.stop_action.setDisabled(True)
        # Stop the timer
        self.simulation_timer.stop()

    def set_current_simulation_date(self, date: ql.Date | datetime.date):
        if isinstance(date, datetime.date):
            date = pydate_to_qldate(date)
        self.current_date = date
        assert isinstance(self.current_date, ql.Date)
        ql.Settings.instance().evaluationDate = self.current_date
        self.view.current_date_label.setText(f"Current date: {self.current_date}")
