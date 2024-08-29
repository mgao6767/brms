import datetime
import time

import QuantLib as ql
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QFileDialog

from brms.controllers import (
    BankingBookController,
    TradingBookController,
    YieldCurveController,
)
from brms.controllers.base import BRMSController
from brms.models.scenario_model import ScenarioModel
from brms.utils import pydate_to_qldate
from brms.views.main_window import MainWindow


class MainController(BRMSController):

    def __init__(self, model: ScenarioModel, view: MainWindow):
        self.scenario: ScenarioModel = model
        self.view: MainWindow = view

        # Initialize the timer
        self.simulation_interval = 500  # o.5 seconds per day
        self.simulation_timer = QTimer()

        # Current date in the simulation
        self.dates_in_simulation: list[ql.Date] = []
        self.current_date: ql.Date = ql.Date()
        self.previous_date: ql.Date = ql.Date()

        # Controllers
        self.yield_curve_controller = YieldCurveController(
            self.scenario.yield_curve_model(),  # model
            self.view.yield_curve_widget,  # view
        )
        self.banking_book_controller = BankingBookController(
            self.scenario.bank_model().banking_book,  # banking book model
            self.view.bank_books_widget.bank_banking_book_widget,  # view
        )
        self.trading_book_controller = TradingBookController(
            self.scenario.bank_model().trading_book,  # trading book model
            self.view.bank_books_widget.bank_trading_book_widget,  # view
        )
        # All controllers
        self._controllers = [
            self.yield_curve_controller,
            self.banking_book_controller,
            self.trading_book_controller,
        ]

        self.connect_signals_slots()

        self.set_current_simulation_date(self.current_date)
        self.set_simulation_speed(self.simulation_interval)

    def reset(self):
        # Reset all child controllers
        for controller in self._controllers:
            controller.reset()
        # Reset main controller itself
        self.simulation_timer.stop()
        self.set_simulation_speed(500)
        # Current date in the simulation
        self.dates_in_simulation.clear()
        self.set_current_simulation_date(ql.Date())
        # At init, only allow Next or Start.
        self.view.next_action.setEnabled(True)
        self.view.start_action.setEnabled(True)
        self.view.pause_action.setDisabled(True)
        self.view.stop_action.setDisabled(True)

    def connect_signals_slots(self):

        self.simulation_timer.timeout.connect(self.on_next_simulation)
        self.view.exit_action.triggered.connect(self.on_exit_action)
        self.view.new_action.triggered.connect(self.on_new_action)
        self.view.open_action.triggered.connect(self.on_open_action)
        self.view.next_action.triggered.connect(self.on_next_simulation)
        self.view.start_action.triggered.connect(self.on_start_action)
        self.view.pause_action.triggered.connect(self.on_pause_action)
        self.view.stop_action.triggered.connect(self.on_stop_action)
        self.view.speed_up_action.triggered.connect(self.on_speed_up_action)
        self.view.speed_down_action.triggered.connect(self.on_speed_down_action)
        self.view.yield_curve_action.triggered.connect(self.on_yield_curve_action)

    # ====== Simulation ========================================================

    def on_exit_action(self):
        self.view.close()

    def on_new_action(self):
        self.reset()

    def on_open_action(self):
        file_dialog = QFileDialog()
        caption = "Load Scenario Data"
        dir = ""
        filter = "Excel Files (*.xlsx)"
        file_path, _ = file_dialog.getOpenFileName(self.view, caption, dir, filter)
        if not file_path:
            return
        self.reset()
        self.load_scenario(file_path)

    def on_next_simulation(self):
        if len(self.dates_in_simulation) == 0:
            self.view.show_warning("No data")
            self.on_stop_action()
            self.reset()
            return

        start_time = time.time()

        idx = self.dates_in_simulation.index(self.current_date)
        if idx >= len(self.dates_in_simulation) - 1:
            self.on_stop_action()
            return
        self.yield_curve_controller.set_current_selection(idx + 1, 0)
        next_date = self.dates_in_simulation[idx + 1]

        self.set_current_simulation_date(next_date)
        self.before_repricing()
        self.repricing()
        self.after_repricing()

        end_time = time.time()
        elapsed_time = (end_time - start_time) * 1000
        self.view.statusBar.showMessage(
            f"Simulation completed in {elapsed_time:.2f} ms."
        )

    def on_start_action(self):
        self.view.statusBar.showMessage("Simulation started.")
        self.view.next_action.setDisabled(True)
        self.view.start_action.setDisabled(True)
        self.view.pause_action.setEnabled(True)
        self.view.stop_action.setEnabled(True)
        self.view.speed_up_action.setEnabled(True)
        self.view.speed_down_action.setEnabled(True)
        self.simulation_timer.start()

    def on_pause_action(self):
        self.view.statusBar.showMessage("Simulation paused.")
        self.view.next_action.setEnabled(True)
        self.view.start_action.setEnabled(True)
        self.view.pause_action.setDisabled(True)
        self.view.stop_action.setDisabled(True)
        self.simulation_timer.stop()

    def on_stop_action(self):
        self.view.statusBar.showMessage("Simulation stopped.")
        self.view.next_action.setDisabled(True)
        self.view.start_action.setDisabled(True)
        self.view.pause_action.setDisabled(True)
        self.view.stop_action.setDisabled(True)
        self.view.speed_up_action.setDisabled(True)
        self.view.speed_down_action.setDisabled(True)
        self.simulation_timer.stop()

    def on_speed_up_action(self):
        # min interval 100ms or 0.1s
        self.simulation_interval = max(100, self.simulation_timer.interval() - 100)
        self.set_simulation_speed(self.simulation_interval)

    def on_speed_down_action(self):
        self.simulation_interval = self.simulation_timer.interval() + 100
        self.set_simulation_speed(self.simulation_interval)

    def on_yield_curve_action(self):
        self.view.yield_curve_widget.show()

    # ==========================================================================
    def before_repricing(self):
        pass

    def repricing(self):
        # yield_curve_ctrl has updated its own `yield_curve`
        # After this, instruments will be revalued, i.e., data in model changed
        self.scenario.relinkable_handle.linkTo(
            self.scenario.yield_curve_model().yield_curve()
        )

        self.banking_book_controller.calculate_payments(
            self.previous_date, self.current_date
        )
        self.trading_book_controller.calculate_payments(
            self.previous_date, self.current_date
        )

    def after_repricing(self):
        self.banking_book_controller.update_assets_tree_view()
        self.banking_book_controller.update_liabilities_tree_view()
        self.trading_book_controller.update_assets_tree_view()
        self.trading_book_controller.update_liabilities_tree_view()

    def set_simulation_speed(self, interval=500):
        text = f"Speed: <u>{interval/1000}</u> sec/day"
        self.simulation_interval = interval
        self.simulation_timer.setInterval(interval)
        self.view.simulation_speed_label.setText(text)

    def set_current_simulation_date(self, date: ql.Date | datetime.date):
        if isinstance(date, datetime.date):
            date = pydate_to_qldate(date)
        self.previous_date = self.current_date
        self.current_date = date
        assert isinstance(self.current_date, ql.Date)
        ql.Settings.instance().evaluationDate = self.current_date
        self.view.current_date_label.setText(
            f"Current Date: <u>{self.current_date}</u>"
        )

    def load_scenario(self, file_path: str):

        if not self.scenario.load_scenario(file_path):
            self.view.show_warning("Failed to load scenario.")

        self.dates_in_simulation = self.scenario.dates_in_simulation()

        self.yield_curve_controller.set_current_selection(0, 0)
        self.set_current_simulation_date(
            self.yield_curve_controller.get_date_from_selection()
        )
        self.scenario.relinkable_handle.linkTo(
            self.scenario.yield_curve_model().yield_curve()
        )

        # For efficiency, when loading scenario, instruments do not emit signals
        # so that views require manual refresh here.
        self.banking_book_controller.update_assets_tree_view()
        self.banking_book_controller.update_liabilities_tree_view()
        self.trading_book_controller.update_assets_tree_view()
        self.trading_book_controller.update_liabilities_tree_view()
        self.banking_book_controller.expand_all_tree_view()
        self.trading_book_controller.expand_all_tree_view()
