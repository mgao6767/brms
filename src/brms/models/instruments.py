from abc import ABC, abstractmethod

import QuantLib as ql

from brms.utils import qldate_to_string


class Instrument(ABC):

    def __init__(self, *args, **kwargs):
        self.instrument = None

    @property
    @abstractmethod
    def name(self):
        pass

    @abstractmethod
    def value_on_banking_book(self, date: ql.Date):
        pass

    @abstractmethod
    def value_on_trading_book(self, date: ql.Date):
        pass


class Cash(Instrument):

    instrument_type = "Cash"

    def __init__(self, value: float):
        self._value = value

    @property
    def name(self):
        return "Cash"

    def value(self):
        return self._value

    def set_value(self, new_value: float):
        self._value = new_value

    def value_on_banking_book(self, date: ql.Date):
        return self.value()

    def value_on_trading_book(self, date: ql.Date):
        return self.value()


class BondLike(ABC):

    def set_pricing_engine(self, engine: ql.PricingEngine):
        self.instrument.setPricingEngine(engine)

    def value(
        self,
        reference_date: ql.Date,
        fixed_forward_rate: float,
        compounding: ql.Compounded | ql.Continuous,  # type: ignore
        comp_frequency: ql.Period,
    ):
        """
        Calculate the present value, clean price, dirty price, and accrued interest of a bond
        using a fixed forward rate.

        Args:
            bond (ql.Bond): The bond object for which the values are calculated.
            reference_date (ql.Date): The reference date for valuation.
            fixed_forward_rate (float): The fixed forward rate used for discounting.
            compounding (ql.Compounded | ql.Continuous): The compounding method.
            comp_frequency (ql.Period): The compounding frequency.

        Returns:
            Tuple[float, float, float, float]: The present value, clean price, dirty price,
            and accrued interest of the bond.
        """

        yield_curve = ql.FlatForward(
            reference_date,
            ql.QuoteHandle(ql.SimpleQuote(fixed_forward_rate)),
            self.instrument.dayCounter(),
            compounding,
            comp_frequency,
        )
        bond_engine = ql.DiscountingBondEngine(ql.YieldTermStructureHandle(yield_curve))

        self.instrument.setPricingEngine(bond_engine)

        # Just being cautious, restore previous evaluation date afterwards
        old_evaluation_date = ql.Settings.instance().evaluationDate

        ql.Settings.instance().evaluationDate = reference_date

        npv = self.instrument.NPV()
        clean_price = self.instrument.cleanPrice()
        dirty_price = self.instrument.dirtyPrice()
        accrued_interest = self.instrument.accruedAmount()

        ql.Settings.instance().evaluationDate = old_evaluation_date

        return npv, clean_price, dirty_price, accrued_interest


class FixedRateBond(Instrument, BondLike):

    instrument_type = "Fixed Rate Bonds"

    def __init__(
        self,
        face_value: float,
        coupon_rate: float,
        issue_date: ql.Date,
        maturity_date: ql.Date,
        frequency: ql.Period = ql.Semiannual,
        settlement_days: int = 0,
        calendar: ql.Calendar = ql.NullCalendar(),
        day_count: ql.DayCounter = ql.Thirty360(ql.Thirty360.BondBasis),
        business_convention=ql.Unadjusted,
        date_generation: ql.DateGeneration = ql.DateGeneration.Backward,
        month_end=False,
    ):
        """
        Builds a fixed rate bond object.

        Args:
            face_value (float): The face value of the bond.
            coupon_rate (float): The coupon rate of the bond.
            issue_date (ql.Date): The issue date of the bond.
            maturity_date (ql.Date): The maturity date of the bond.
            frequency (ql.Period, optional): The frequency of coupon payments. Defaults to ql.Semiannual.
            settlement_days (int, optional): The number of settlement days. Defaults to 0.
            calendar (ql.Calendar, optional): The calendar used for date calculations. Defaults to ql.NullCalendar().
            day_count (ql.DayCounter, optional): The day count convention for interest calculations. Defaults to ql.Thirty360(ql.Thirty360.BondBasis).
            business_convention (int, optional): The business convention for date adjustment. Defaults to ql.Unadjusted.
            date_generation (ql.DateGeneration, optional): The date generation rule for coupon dates. Defaults to ql.DateGeneration.Backward.
            month_end (bool, optional): Whether the coupon dates should be adjusted to the end of the month. Defaults to False.
        """
        maturity_date_str = qldate_to_string(maturity_date)
        self._name = f"{coupon_rate*100:.2f}% {maturity_date_str}"

        coupons = [coupon_rate]
        tenor = ql.Period(frequency)

        schedule = ql.Schedule(
            issue_date,
            maturity_date,
            tenor,
            calendar,
            business_convention,
            business_convention,
            date_generation,
            month_end,
        )

        self.instrument = ql.FixedRateBond(
            settlement_days, face_value, schedule, coupons, day_count
        )

    @property
    def name(self):
        return self._name

    def value_on_banking_book(self, date: ql.Date):
        return self.instrument.notional(date)

    def value_on_trading_book(self, date: ql.Date):
        return self.instrument.NPV()

    def payment_schedule(self):
        """
        Generates the payment schedule for a bond.

        Returns:
            list: A list of tuples representing the payment schedule. Each tuple contains the payment date and amount.
        """
        return [(cf.date(), cf.amount()) for cf in self.instrument.cashflows()]


class TreasuryBill(Instrument):
    pass


class TreasuryNote(FixedRateBond):

    instrument_type = "Treasury Notes"


class TreasuryBond(FixedRateBond):

    instrument_type = "Treasury Bonds"


class Loan(Instrument):
    pass


class AmortizingFixedRateLoan(Loan, BondLike):

    instrument_type = "Amortizing Loans"

    def __init__(
        self,
        face_value: float,
        interest_rate: float,
        issue_date: ql.Date,
        maturity: ql.Period,
        frequency: ql.Period = ql.Semiannual,
        settlement_days: int = 0,
        calendar: ql.Calendar = ql.NullCalendar(),
        day_count: ql.DayCounter = ql.Thirty360(ql.Thirty360.BondBasis),
        business_convention=ql.Unadjusted,
    ):
        """
        Initializes an instance of the Instruments class.
        Args:
            face_value (float): The face value of the instrument.
            interest_rate (float): The interest rate of the instrument.
            issue_date (ql.Date): The issue date of the instrument.
            maturity (ql.Period): The maturity period of the instrument.
            frequency (ql.Period, optional): The frequency of coupon payments. Defaults to ql.Semiannual.
            settlement_days (int, optional): The number of settlement days. Defaults to 0.
            calendar (ql.Calendar, optional): The calendar used for date calculations. Defaults to ql.NullCalendar().
            day_count (ql.DayCounter, optional): The day count convention used for interest calculations. Defaults to ql.Thirty360(ql.Thirty360.BondBasis).
            business_convention (int, optional): The business convention used for date adjustments. Defaults to ql.Unadjusted.
        """
        maturity_date_str = qldate_to_string(issue_date + maturity)
        self._name = f"{interest_rate*100:.2f}% {maturity_date_str}"

        coupons = [interest_rate]
        schedule = ql.sinkingSchedule(issue_date, maturity, frequency, calendar)
        notionals = ql.sinkingNotionals(maturity, frequency, interest_rate, face_value)

        self.instrument = ql.AmortizingFixedRateBond(
            settlement_days,
            notionals,
            schedule,
            coupons,
            day_count,
            business_convention,
            issue_date,
        )

    @property
    def name(self):
        return self._name

    def value_on_banking_book(self, date: ql.Date):
        return self.instrument.notional(date)

    def value_on_trading_book(self, date: ql.Date):
        return self.instrument.NPV()

    def payment_schedule(self):
        """
        Calculate the payment schedule for the instrument.
        Returns:
            Tuple: A tuple containing three lists:
                - interest_pmt: A list of tuples representing the date and amount of interest payments.
                - principal_pmt: A list of tuples representing the date and amount of principal payments.
                - outstanding: A list of tuples representing the date and outstanding balance after each payment.
        """
        loan = self.instrument
        interest_pmt = []
        principal_pmt = []
        outstanding = []
        last_outstanding = loan.notional(loan.issueDate())
        for i, cf in enumerate(loan.cashflows()):
            if i % 2 == 0:
                interest_pmt.append((cf.date(), cf.amount()))
            else:
                principal_pmt.append((cf.date(), cf.amount()))
                outstanding.append((cf.date(), last_outstanding - cf.amount()))
                _, last_outstanding = outstanding[-1]

        return interest_pmt, principal_pmt, outstanding


class ConsumerLoan(Loan):
    pass


class CILoan(Loan):
    pass


class Mortgage(AmortizingFixedRateLoan):

    instrument_type = "Mortgages"

    def __init__(
        self,
        face_value: float,
        interest_rate: float,
        issue_date: ql.Date,
        maturity: ql.Period,
        frequency: ql.Period = ql.Semiannual,
        settlement_days: int = 0,
        calendar: ql.Calendar = ql.NullCalendar(),
        day_count: ql.DayCounter = ql.Thirty360(ql.Thirty360.BondBasis),
        business_convention=ql.Unadjusted,
    ):

        super().__init__(
            face_value,
            interest_rate,
            issue_date,
            maturity,
            frequency,
            settlement_days,
            calendar,
            day_count,
            business_convention,
        )


class CommercialPaper(Loan):
    pass


class MediumTermNote(Loan):
    pass


class DemandDeposit(Instrument):

    instrument_type = "Demand Deposits"

    def __init__(self, value: float):
        self._value = value

    @property
    def name(self):
        return "Non-interest bearing"

    def value(self):
        return self._value

    def set_value(self, new_value: float):
        self._value = new_value

    def value_on_banking_book(self, date: ql.Date):
        return self.value()

    def value_on_trading_book(self, date: ql.Date):
        return self.value()


class TermDeposit(Instrument):
    pass


class CertificateOfDeposit(Instrument):
    pass


class Stock(Instrument):
    pass


class StockOption(Instrument):
    pass


class ForwardRateAgreement(Instrument):
    pass


class InterestRateSwap(Instrument):
    pass


class TreasuryFutures(Instrument):
    pass


class InstrumentFactory:

    @staticmethod
    def create_demand_deposits(value: float):
        return DemandDeposit(value)

    @staticmethod
    def create_cash(value: float):
        return Cash(value)

    @staticmethod
    def create_fixed_rate_bond(
        face_value: float,
        coupon_rate: float,
        issue_date: ql.Date,
        maturity_date: ql.Date,
        frequency: ql.Period = ql.Semiannual,
        settlement_days: int = 0,
        calendar: ql.Calendar = ql.NullCalendar(),
        day_count: ql.DayCounter = ql.Thirty360(ql.Thirty360.BondBasis),
        business_convention=ql.Unadjusted,
        date_generation: ql.DateGeneration = ql.DateGeneration.Backward,
        month_end=False,
    ) -> FixedRateBond:

        return FixedRateBond(
            face_value,
            coupon_rate,
            issue_date,
            maturity_date,
            frequency,
            settlement_days,
            calendar,
            day_count,
            business_convention,
            date_generation,
            month_end,
        )

    @staticmethod
    def create_treasury_note(
        face_value: float,
        coupon_rate: float,
        issue_date: ql.Date,
        maturity_date: ql.Date,
        frequency: ql.Period = ql.Semiannual,
        settlement_days: int = 0,
        calendar: ql.Calendar = ql.NullCalendar(),
        day_count: ql.DayCounter = ql.Thirty360(ql.Thirty360.BondBasis),
        business_convention=ql.Unadjusted,
        date_generation: ql.DateGeneration = ql.DateGeneration.Backward,
        month_end=False,
    ) -> TreasuryNote:

        return TreasuryNote(
            face_value,
            coupon_rate,
            issue_date,
            maturity_date,
            frequency,
            settlement_days,
            calendar,
            day_count,
            business_convention,
            date_generation,
            month_end,
        )

    @staticmethod
    def create_treasury_bond(
        face_value: float,
        coupon_rate: float,
        issue_date: ql.Date,
        maturity_date: ql.Date,
        frequency: ql.Period = ql.Semiannual,
        settlement_days: int = 0,
        calendar: ql.Calendar = ql.NullCalendar(),
        day_count: ql.DayCounter = ql.Thirty360(ql.Thirty360.BondBasis),
        business_convention=ql.Unadjusted,
        date_generation: ql.DateGeneration = ql.DateGeneration.Backward,
        month_end=False,
    ) -> TreasuryBond:

        return TreasuryBond(
            face_value,
            coupon_rate,
            issue_date,
            maturity_date,
            frequency,
            settlement_days,
            calendar,
            day_count,
            business_convention,
            date_generation,
            month_end,
        )

    @staticmethod
    def create_fixed_rate_amortizing_loan(
        face_value: float,
        interest_rate: float,
        issue_date: ql.Date,
        maturity: ql.Period,
        frequency: ql.Period = ql.Semiannual,
        settlement_days: int = 0,
        calendar: ql.Calendar = ql.NullCalendar(),
        day_count: ql.DayCounter = ql.Thirty360(ql.Thirty360.BondBasis),
        business_convention=ql.Unadjusted,
    ) -> AmortizingFixedRateLoan:

        return AmortizingFixedRateLoan(
            face_value,
            interest_rate,
            issue_date,
            maturity,
            frequency,
            settlement_days,
            calendar,
            day_count,
            business_convention,
        )

    @staticmethod
    def create_fixed_rate_mortgage(
        face_value: float,
        interest_rate: float,
        issue_date: ql.Date,
        maturity: ql.Period,
        frequency: ql.Period = ql.Semiannual,
        settlement_days: int = 0,
        calendar: ql.Calendar = ql.NullCalendar(),
        day_count: ql.DayCounter = ql.Thirty360(ql.Thirty360.BondBasis),
        business_convention=ql.Unadjusted,
    ) -> Mortgage:

        return Mortgage(
            face_value,
            interest_rate,
            issue_date,
            maturity,
            frequency,
            settlement_days,
            calendar,
            day_count,
            business_convention,
        )
