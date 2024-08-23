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

        # Create the pricing engine
        self.relinkable_handle = ql.RelinkableYieldTermStructureHandle()
        self.bond_pricing_engine = ql.DiscountingBondEngine(self.relinkable_handle)

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
        self.relinkable_handle.linkTo(self.view.yield_curve_ctrl.yield_curve)

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

        # yield_curve_ctrl has updated its own `yield_curve`
        # After this, instruments will be revalued, i.e., data in model changed
        self.relinkable_handle.linkTo(self.view.yield_curve_ctrl.yield_curve)

        self.banking_book_controller.update_assets_tree_view()
        self.banking_book_controller.update_liabilities_tree_view()
        self.trading_book_controller.update_assets_tree_view()
        self.trading_book_controller.update_liabilities_tree_view()

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

    # ====== Testing func to populate the books =================================
    def _test_setup(self):
        from brms.models.instruments import InstrumentFactory

        cash = InstrumentFactory.create_cash(1_000_000.0)
        self.banking_book_controller.add_asset(cash)

        depo = InstrumentFactory.create_demand_deposits(2_000_000.0)
        self.banking_book_controller.add_liability(depo)

        self._mock_mortgages()
        self._mock_ci_loans()
        self._mock_treasury_notes()
        self._mock_treasury_bonds()

        # Manually refresh so that all colors start with black
        self.banking_book_controller.update_assets_tree_view()
        self.banking_book_controller.update_liabilities_tree_view()
        self.trading_book_controller.update_assets_tree_view()
        self.trading_book_controller.update_liabilities_tree_view()

    def _mock_mortgages(self):
        from brms.models.instruments import InstrumentFactory

        ctrl = self.view.loan_calculator_ctrl
        _, params = ctrl.build_loan()

        (
            principal,
            annual_rate,
            start_date,
            maturity,
            payment_frequency,
            settlement_days,
            calendar_ql,
            day_count,
            business_convention,
        ) = params[4:]

        ref_date = ql.Settings.instance().evaluationDate

        # Mock case 1: 30-year fixed-rate mortgage issued 1 year ago
        start_date = ref_date - ql.Period(1, ql.Years)
        mortgage_30yr = InstrumentFactory.create_fixed_rate_mortgage(
            900_000,
            5.5 / 100,
            start_date,
            ql.Period(30, ql.Years),  # term_years
            payment_frequency,
            settlement_days,
            calendar_ql,
            day_count,
            business_convention,
        )
        mortgage_30yr.set_pricing_engine(self.bond_pricing_engine)
        self.banking_book_controller.add_asset(mortgage_30yr)

        # Mock case 2: 15-year fixed-rate mortgage issued 6 months ago
        start_date = ref_date - ql.Period(6, ql.Months)
        mortgage_15yr = InstrumentFactory.create_fixed_rate_mortgage(
            800_000,
            6.2 / 100,  # interest rate
            start_date,
            ql.Period(15, ql.Years),  # term_years
            payment_frequency,
            settlement_days,
            calendar_ql,
            day_count,
            business_convention,
        )
        mortgage_15yr.set_pricing_engine(self.bond_pricing_engine)
        self.banking_book_controller.add_asset(mortgage_15yr)

        # Mock case 3: 20-year fixed-rate mortgage issued 3 months ago
        start_date = ref_date - ql.Period(3, ql.Months)
        mortgage_5yr = InstrumentFactory.create_fixed_rate_mortgage(
            1_000_000,
            6.5 / 100,  # interest rate,
            start_date,
            ql.Period(20, ql.Years),  # term_years
            payment_frequency,
            settlement_days,
            calendar_ql,
            day_count,
            business_convention,
        )
        mortgage_5yr.set_pricing_engine(self.bond_pricing_engine)
        self.banking_book_controller.add_asset(mortgage_5yr)

    def _mock_ci_loans(self):
        from brms.models.instruments import InstrumentFactory

        ctrl = self.view.bond_calculator_ctrl
        _, params = ctrl.build_bond()

        (
            face_value,
            coupon_rate,
            issue_date,
            maturity_date,
            frequency,
            settlement_days,
            calendar_ql,
            day_count,
            business_convention,
            date_generation,
        ) = params[4:]

        ref_date = ql.Settings.instance().evaluationDate

        # 8% 10yr C&I loan issued 8 months ago
        issue_date = ref_date - ql.Period(8, ql.Months)
        loan = InstrumentFactory.create_ci_loan(
            5_000_000,
            8.0 / 100,  # interest rate
            issue_date,
            issue_date + ql.Period(10, ql.Years),  # maturity_date,
            frequency,
            settlement_days,
            calendar_ql,
            day_count,
            business_convention,
            date_generation,
        )
        loan.set_pricing_engine(self.bond_pricing_engine)
        self.banking_book_controller.add_asset(loan)

        # 7.5% 5yr C&I loan issued 2yrs ago
        issue_date = ref_date - ql.Period(2, ql.Years)
        loan = InstrumentFactory.create_ci_loan(
            3_800_000,
            7.5 / 100,  # interest rate
            issue_date,
            issue_date + ql.Period(5, ql.Years),  # maturity_date,
            frequency,
            settlement_days,
            calendar_ql,
            day_count,
            business_convention,
            date_generation,
        )
        loan.set_pricing_engine(self.bond_pricing_engine)
        self.banking_book_controller.add_asset(loan)

    def _mock_treasury_notes(self):
        from brms.models.instruments import InstrumentFactory

        ctrl = self.view.bond_calculator_ctrl
        _, params = ctrl.build_bond()

        (
            face_value,
            coupon_rate,
            issue_date,
            maturity_date,
            frequency,
            settlement_days,
            calendar_ql,
            day_count,
            business_convention,
            date_generation,
        ) = params[4:]

        ref_date = ql.Settings.instance().evaluationDate
        face_value = 10_000_000

        # 0.45% 2yr TN issued 6m ago
        issue_date = ref_date - ql.Period(6, ql.Months)
        treasury_note = InstrumentFactory.create_treasury_note(
            face_value,
            0.45 / 100,  # coupon_rate
            issue_date,
            issue_date + ql.Period(2, ql.Years),  # maturity_date,
            frequency,
            settlement_days,
            calendar_ql,
            day_count,
            business_convention,
            date_generation,
        )
        treasury_note.set_pricing_engine(self.bond_pricing_engine)
        self.trading_book_controller.add_asset(treasury_note)

        # 1.2% 5yr TN issued 10m ago
        issue_date = ref_date - ql.Period(10, ql.Months)
        treasury_note = InstrumentFactory.create_treasury_note(
            face_value,
            1.2 / 100,  # coupon_rate
            issue_date,
            issue_date + ql.Period(5, ql.Years),  # maturity_date,
            frequency,
            settlement_days,
            calendar_ql,
            day_count,
            business_convention,
            date_generation,
        )
        treasury_note.set_pricing_engine(self.bond_pricing_engine)
        self.trading_book_controller.add_asset(treasury_note)

        # 1.5% 7yr TN issued 1m ago
        issue_date = ref_date - ql.Period(1, ql.Months)
        treasury_note = InstrumentFactory.create_treasury_note(
            face_value,
            1.5 / 100,  # coupon_rate
            issue_date,
            issue_date + ql.Period(7, ql.Years),  # maturity_date,
            frequency,
            settlement_days,
            calendar_ql,
            day_count,
            business_convention,
            date_generation,
        )
        treasury_note.set_pricing_engine(self.bond_pricing_engine)
        self.trading_book_controller.add_asset(treasury_note)

    def _mock_treasury_bonds(self):
        from brms.models.instruments import InstrumentFactory

        ctrl = self.view.bond_calculator_ctrl
        _, params = ctrl.build_bond()

        (
            face_value,
            coupon_rate,
            issue_date,
            maturity_date,
            frequency,
            settlement_days,
            calendar_ql,
            day_count,
            business_convention,
            date_generation,
        ) = params[4:]

        ref_date = ql.Settings.instance().evaluationDate
        face_value = 10_000_000

        # 2% 20yr TB issued 1yr ago
        issue_date = ref_date - ql.Period(12, ql.Months)
        treasury_bond = InstrumentFactory.create_treasury_bond(
            face_value,
            2.0 / 100,  # coupon_rate
            issue_date,
            issue_date + ql.Period(20, ql.Years),  # maturity_date,
            frequency,
            settlement_days,
            calendar_ql,
            day_count,
            business_convention,
            date_generation,
        )
        treasury_bond.set_pricing_engine(self.bond_pricing_engine)
        self.trading_book_controller.add_asset(treasury_bond)

        # 3% 30yr TB issued 2yr ago
        issue_date = ref_date - ql.Period(24, ql.Months)
        treasury_bond = InstrumentFactory.create_treasury_bond(
            face_value * 0.5,
            3.0 / 100,  # coupon_rate
            issue_date,
            issue_date + ql.Period(30, ql.Years),  # maturity_date,
            frequency,
            settlement_days,
            calendar_ql,
            day_count,
            business_convention,
            date_generation,
        )
        treasury_bond.set_pricing_engine(self.bond_pricing_engine)
        self.trading_book_controller.add_liability(treasury_bond)
