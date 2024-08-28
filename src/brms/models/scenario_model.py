import os

import pandas as pd
import QuantLib as ql
from PySide6.QtCore import QObject, Signal

from brms.models.bank_model import BankModel
from brms.models.instruments import InstrumentFactory
from brms.models.yield_curve_model import YieldCurveModel
from brms.utils import pydate_to_qldate, qldate_to_string


class ScenarioModel(QObject):

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)

        self._scenario_file_path: str = ""
        self._dates_in_simulation: list[ql.Date] = []
        self.bank = BankModel()
        self.yield_curve = YieldCurveModel()
        # Create the pricing engine
        self.relinkable_handle = ql.RelinkableYieldTermStructureHandle()
        self.bond_pricing_engine = ql.DiscountingBondEngine(self.relinkable_handle)

    def reset(self) -> None:
        """
        Reset the scenario model by clearing the scenario file path.
        """

        self._scenario_file_path = ""

    def bank_model(self) -> BankModel:
        """
        Return the bank model associated with this scenario.

        :return: The bank model.
        :rtype: BankModel
        """

        return self.bank

    def yield_curve_model(self) -> YieldCurveModel:
        """
        Return the yield curve model associated with this scenario.

        :return: The yield curve model.
        :rtype: YieldCurveModel
        """

        return self.yield_curve

    def dates_in_simulation(self) -> list[ql.Date]:
        """
        Return the list of dates in the simulation.

        :return: A list of `ql.Date` objects representing the dates in the simulation.
        :rtype: list[ql.Date]
        """

        return self._dates_in_simulation

    def on_payments_received(self, payment: float) -> None:
        """
        Process the received payment and update the cash balance in the banking book.

        :param payment: The amount of payment received.
        :type payment: float
        """

        cash = self.bank_model().banking_book.get_cash()
        self.bank_model().banking_book.set_cash(cash + payment)

    def on_payments_paid(self, payment: float) -> None:
        """
        Process the paid payment and update the cash balance in the banking book.

        :param payment: The amount of payment paid.
        :type payment: float
        """

        cash = self.bank_model().banking_book.get_cash()
        self.bank_model().banking_book.set_cash(cash - payment)

    def load_scenario(self, file_path: str) -> bool:
        """
        Load a scenario from the given file path.

        :param file_path: The path to the scenario file.
        :type file_path: str
        :return: True if the scenario is loaded successfully, False otherwise.
        :rtype: bool
        """

        if not os.path.exists(file_path):
            return False
        self._scenario_file_path = file_path
        return all(
            [
                self.load_meta(),
                self.load_yield_curve(),
                self.load_mortgages(),
                self.load_ci_loans(),
                self.load_treasury_notes(long_position=True),
                self.load_treasury_notes(long_position=False),
                self.load_treasury_bonds(long_position=True),
                self.load_treasury_bonds(long_position=False),
            ]
        )

    def load_meta(self) -> bool:
        """
        Load meta data from the scenario file (Excel file).

        :return: True if the meta data is loaded successfully, False otherwise.
        :rtype: bool
        """

        _file_path = self._scenario_file_path
        try:
            df = pd.read_excel(_file_path, sheet_name="Meta", header=None)
        except Exception:
            return False

        df.columns = ["item", "value"]
        try:
            cash_value = df.loc[df["item"] == "Cash", "value"].values[0]
            self.bank.add_cash(cash_value)
            deposits_value = df.loc[df["item"] == "Demand deposits", "value"].values[0]
            self.bank.add_demand_deposits(deposits_value)
        except Exception:
            return False

        return True

    def load_yield_curve(self) -> bool:
        """
        Load the yield curve data from the scenario file (Excel file).

        The yields data is stored in `self.yield_curve_model`, instance of :class:`YieldCurveModel`.

        :return: True if the yield curve data is successfully loaded, False otherwise.
        :rtype: bool
        """

        _file_path = self._scenario_file_path
        try:
            df = pd.read_excel(_file_path, sheet_name="Yield Curve", index_col="Date")
        except Exception:
            return False
        # A dict where key is reference date, value is a list of (maturity, rate)
        yield_data = {
            row.name: [(mat, rate) for mat, rate in zip(row.index, row.to_list())]
            for _, row in df.iterrows()
        }
        self.yield_curve_model().update_yield_data(yield_data)

        # TODO: Should this be here?
        self._dates_in_simulation = [
            pydate_to_qldate(date)
            for date in self.yield_curve_model().reference_dates()
        ]

        return True

    def load_mortgages(self) -> bool:
        """
        Load the mortgages data from the scenario file (Excel file).

        The mortgages are stored by the bank's banking book model
        as instances of :class:`FixedRateMortgages`.

        :return: True if the mortgages data is successfully loaded, False otherwise.
        :rtype: bool
        """

        try:
            df = pd.read_excel(self._scenario_file_path, sheet_name="Mortgages")
        except Exception:
            return False

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
            mortgage.set_pricing_engine(self.bond_pricing_engine)
            mortgage.payments_paid.connect(self.on_payments_paid)
            mortgage.payments_received.connect(self.on_payments_received)
            self.bank_model().banking_book.add_asset(mortgage, emit_signal=False)

        return True

    def load_ci_loans(self) -> bool:
        """
        Loads the C&I loans data from the scenario file (Excel file).

        The C&I loans are stored by the bank's banking book model
        as instances of :class:`CILoan`.

        :return: True if the C&I loans data is successfully loaded, False otherwise.
        :rtype: bool
        """

        try:
            df = pd.read_excel(self._scenario_file_path, sheet_name="C&I Loans")
        except Exception:
            return False

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
            loan.set_pricing_engine(self.bond_pricing_engine)
            loan.payments_paid.connect(self.on_payments_paid)
            loan.payments_received.connect(self.on_payments_received)
            self.bank_model().banking_book.add_asset(loan, emit_signal=False)

        return True

    def load_treasury_notes(self, long_position=True) -> bool:
        """
        Load the Treasury Notes data from the scenario file (Excel file).

        :param long_position: A boolean indicating whether the position is long or short. Default is True.
        :type long_position: bool
        :return: True if the Treasury Notes data is successfully loaded, False otherwise.
        :rtype: bool
        """

        sheet_name = f"Treasury Notes ({'Long' if long_position else 'Short'})"
        try:
            df = pd.read_excel(self._scenario_file_path, sheet_name=sheet_name)
        except Exception:
            return False

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
            tn.set_pricing_engine(self.bond_pricing_engine)
            if long_position:
                tn.payments_paid.connect(self.on_payments_paid)
                tn.payments_received.connect(self.on_payments_received)
                self.bank_model().trading_book.add_asset(tn, emit_signal=False)
            else:
                tn.payments_paid.connect(self.on_payments_received)
                tn.payments_received.connect(self.on_payments_paid)
                self.bank_model().trading_book.add_liability(tn, emit_signal=False)

        return True

    def load_treasury_bonds(self, long_position=True) -> bool:
        """
        Load the Treasury Bonds data from the scenario file (Excel file).

        :param long_position: A boolean indicating whether the position is long or short. Default is True.
        :type long_position: bool
        :return: True if the Treasury Bonds data is successfully loaded, False otherwise.
        :rtype: bool
        """

        sheet_name = f"Treasury Bonds ({'Long' if long_position else 'Short'})"
        try:
            df = pd.read_excel(self._scenario_file_path, sheet_name=sheet_name)
        except Exception:
            return False

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
                tb = InstrumentFactory.create_treasury_bond(
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
            tb.set_pricing_engine(self.bond_pricing_engine)
            if long_position:
                tb.payments_paid.connect(self.on_payments_paid)
                tb.payments_received.connect(self.on_payments_received)
                self.bank_model().trading_book.add_asset(tb, emit_signal=False)
            else:
                tb.payments_paid.connect(self.on_payments_received)
                tb.payments_received.connect(self.on_payments_paid)
                self.bank_model().trading_book.add_liability(tb, emit_signal=False)

        return True
