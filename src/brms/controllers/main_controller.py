import datetime

import pandas as pd
import QuantLib as ql
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QFileDialog

from brms.controllers import BankingBookController, TradingBookController
from brms.controllers.base import BRMSController
from brms.models.bank_model import BankModel
from brms.models.instruments import InstrumentFactory
from brms.utils import pydate_to_qldate
from brms.views.main_window import MainWindow


class MainController(BRMSController):

    def __init__(self, model: BankModel, view: MainWindow):
        self.model = model
        self.view = view

        # Initialize the timer
        self.simulation_interval = 500  # o.5 seconds per day
        self.simulation_timer = QTimer()
        self.set_simulation_speed(self.simulation_interval)

        # Create the pricing engine
        self.relinkable_handle = ql.RelinkableYieldTermStructureHandle()
        self.bond_pricing_engine = ql.DiscountingBondEngine(self.relinkable_handle)

        # Current date in the simulation
        self.dates_in_simulation = []
        self.current_date: ql.Date = ql.Date()
        self.previous_date: ql.Date = ql.Date()

        # book models
        self.banking_book = self.model.banking_book
        self.trading_book = self.model.trading_book

        # book view/widget
        self.banking_book_widget = self.view.bank_books_widget.bank_banking_book_widget
        self.trading_book_widget = self.view.bank_books_widget.bank_trading_book_widget

        # fmt: off
        self.banking_book_controller = BankingBookController(self.banking_book, self.banking_book_widget)
        self.trading_book_controller = TradingBookController(self.trading_book, self.trading_book_widget)

        # All controllers
        self._controllers = [
            self.banking_book_controller,
            self.trading_book_controller,
        ]

        self.connect_signals_slots()
        self.post_init()

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

    def post_init(self):
        # TODO: yield data should come from scenario data
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
        self.relinkable_handle.linkTo(self.view.yield_curve_ctrl.yield_curve)

    def reset(self):
        # Reset all child controllers
        for controller in self._controllers:
            controller.reset()
        # Reset main controller itself
        self.simulation_timer.stop()
        self.set_simulation_speed(500)

    # ====== Simulation ========================================================

    def on_exit_action(self):
        self.view.close()

    def on_new_action(self):
        self.reset()

    def on_open_action(self):
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(
            self.view, "Load Scenario Data", "", "Excel Files (*.xlsx)"
        )
        if not file_path:
            return
        self.reset()
        self.load_scenario(file_path)

    def on_next_simulation(self):
        self.view.statusBar.showMessage("Simulation moved to next period.")
        idx = self.dates_in_simulation.index(self.current_date)
        if idx >= len(self.dates_in_simulation) - 1:
            self.on_stop_simulation()
            return
        self.view.yield_curve_ctrl.set_current_selection(idx + 1, 0)
        next_date = self.dates_in_simulation[idx + 1]

        self.set_current_simulation_date(next_date)
        self.before_repricing()
        self.repricing()
        self.after_repricing()

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
        self.relinkable_handle.linkTo(self.view.yield_curve_ctrl.yield_curve)

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

        self._scenario_file_path = file_path

        try:
            self._load_meta()
            self._load_mortgages()
            self._load_ci_loans()
            self._load_treasury_notes(long_position=True)
            self._load_treasury_notes(long_position=False)
            self._load_treasury_bonds(long_position=True)
            self._load_treasury_bonds(long_position=False)
        except Exception as err:
            self.view.statusBar.showMessage("Failed to load scenario data")
            print(err)

        self.banking_book_controller.expand_all_tree_view()
        self.trading_book_controller.expand_all_tree_view()
        # Manually refresh so that all colors start with black
        self.banking_book_controller.update_assets_tree_view()
        self.banking_book_controller.update_liabilities_tree_view()
        self.trading_book_controller.update_assets_tree_view()
        self.trading_book_controller.update_liabilities_tree_view()

    def _load_meta(self):

        df = pd.read_excel(self._scenario_file_path, sheet_name="Meta", header=None)
        df.columns = ["item", "value"]

        cash_value = df.loc[df["item"] == "Cash", "value"].values[0]
        cash = InstrumentFactory.create_cash(cash_value)
        self.banking_book_controller.add_asset(cash)

        deposits_value = df.loc[df["item"] == "Demand deposits", "value"].values[0]
        deposits = InstrumentFactory.create_demand_deposits(deposits_value)
        self.banking_book_controller.add_liability(deposits)

        equity_value = df.loc[df["item"] == "Common equity", "value"].values[0]
        equity = InstrumentFactory.create_common_equity(equity_value)
        self.banking_book_controller.add_liability(equity)

    def _load_mortgages(self):

        df = pd.read_excel(self._scenario_file_path, sheet_name="Mortgages")
        if not isinstance(df, pd.DataFrame):
            return

        settlement_days = 0
        calendar_ql = ql.NullCalendar()
        day_count = ql.ActualActual(ql.ActualActual.ISDA)
        business_convention = ql.Following

        for _, row in df.iterrows():
            principal = row["principal"]
            annual_rate = row["interest_rate"]
            start_date = pydate_to_qldate(row["issue_date"])
            maturity = ql.Period(row["maturity_years"], ql.Years)
            match row["payment_frequency"]:
                case "quarterly" | "Quarterly":
                    payment_frequency = ql.Quarterly
                case _:
                    payment_frequency = ql.Monthly
            try:
                mortgage = InstrumentFactory.create_fixed_rate_mortgage(
                    principal,
                    annual_rate,
                    start_date,
                    maturity,
                    payment_frequency,
                    settlement_days,
                    calendar_ql,
                    day_count,
                    business_convention,
                )
            except Exception:
                continue
            # fmt: off
            mortgage.set_pricing_engine(self.bond_pricing_engine)
            mortgage.payments_paid.connect(self.banking_book_controller.process_payments_paid)
            mortgage.payments_received.connect(self.banking_book_controller.process_payments_received)
            self.banking_book_controller.add_asset(mortgage)

    def _load_ci_loans(self):

        df = pd.read_excel(self._scenario_file_path, sheet_name="C&I Loans")
        if not isinstance(df, pd.DataFrame):
            return

        settlement_days = 0
        calendar_ql = ql.NullCalendar()
        day_count = ql.ActualActual(ql.ActualActual.ISDA)
        business_convention = ql.Following
        date_generation = ql.DateGeneration.Backward

        for _, row in df.iterrows():
            principal = row["principal"]
            annual_rate = row["interest_rate"]
            issue_date = pydate_to_qldate(row["issue_date"])
            maturity_date = pydate_to_qldate(row["maturity_date"])
            match row["payment_frequency"]:
                case "quarterly" | "Quarterly":
                    payment_frequency = ql.Quarterly
                case _:
                    payment_frequency = ql.Monthly
            try:
                loan = InstrumentFactory.create_ci_loan(
                    principal,
                    annual_rate,
                    issue_date,
                    maturity_date,
                    payment_frequency,
                    settlement_days,
                    calendar_ql,
                    day_count,
                    business_convention,
                    date_generation,
                )
            except Exception:
                continue
            # fmt: off
            loan.set_pricing_engine(self.bond_pricing_engine)
            loan.payments_paid.connect(self.banking_book_controller.process_payments_paid)
            loan.payments_received.connect(self.banking_book_controller.process_payments_received)
            self.banking_book_controller.add_asset(loan)

    def _load_treasury_notes(self, long_position=True):

        # fmt: off
        if long_position:
            df = pd.read_excel(self._scenario_file_path, sheet_name="Treasury Notes (Long)")
        else:
            df = pd.read_excel(self._scenario_file_path, sheet_name="Treasury Notes (Short)")
        if not isinstance(df, pd.DataFrame):
            return
        # fmt: on

        settlement_days = 0
        calendar_ql = ql.NullCalendar()
        day_count = ql.ActualActual(ql.ActualActual.ISDA)
        business_convention = ql.Following
        date_generation = ql.DateGeneration.Backward

        for _, row in df.iterrows():
            principal = row["principal"]
            annual_rate = row["interest_rate"]
            issue_date = pydate_to_qldate(row["issue_date"])
            maturity_date = pydate_to_qldate(row["maturity_date"])
            payment_frequency = ql.Semiannual
            try:
                tn = InstrumentFactory.create_treasury_note(
                    principal,
                    annual_rate,
                    issue_date,
                    maturity_date,
                    payment_frequency,
                    settlement_days,
                    calendar_ql,
                    day_count,
                    business_convention,
                    date_generation,
                )
            except Exception:
                continue
            # fmt: off
            tn.set_pricing_engine(self.bond_pricing_engine)
            if long_position:
                tn.payments_paid.connect(self.banking_book_controller.process_payments_paid)
                tn.payments_received.connect(self.banking_book_controller.process_payments_received)
                self.trading_book_controller.add_asset(tn)
            else:
                tn.payments_paid.connect(self.banking_book_controller.process_payments_received)
                tn.payments_received.connect(self.banking_book_controller.process_payments_paid)
                self.trading_book_controller.add_liability(tn)

    def _load_treasury_bonds(self, long_position=True):

        # fmt: off
        if long_position:
            df = pd.read_excel(self._scenario_file_path, sheet_name="Treasury Bonds (Long)")
        else:
            df = pd.read_excel(self._scenario_file_path, sheet_name="Treasury Bonds (Short)")
        if not isinstance(df, pd.DataFrame):
            return
        # fmt: on

        settlement_days = 0
        calendar_ql = ql.NullCalendar()
        day_count = ql.ActualActual(ql.ActualActual.ISDA)
        business_convention = ql.Following
        date_generation = ql.DateGeneration.Backward

        for _, row in df.iterrows():
            principal = row["principal"]
            annual_rate = row["interest_rate"]
            issue_date = pydate_to_qldate(row["issue_date"])
            maturity_date = pydate_to_qldate(row["maturity_date"])
            payment_frequency = ql.Semiannual
            try:
                tn = InstrumentFactory.create_treasury_bond(
                    principal,
                    annual_rate,
                    issue_date,
                    maturity_date,
                    payment_frequency,
                    settlement_days,
                    calendar_ql,
                    day_count,
                    business_convention,
                    date_generation,
                )
            except Exception:
                continue
            # fmt: off
            tn.set_pricing_engine(self.bond_pricing_engine)
            if long_position:
                tn.payments_paid.connect(self.banking_book_controller.process_payments_paid)
                tn.payments_received.connect(self.banking_book_controller.process_payments_received)
                self.trading_book_controller.add_asset(tn)
            else:
                tn.payments_paid.connect(self.banking_book_controller.process_payments_received)
                tn.payments_received.connect(self.banking_book_controller.process_payments_paid)
                self.trading_book_controller.add_liability(tn)
