import QuantLib as ql


class BondModel:

    def __init__(self) -> None:
        pass

    def build_fixed_rate_bond(
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
    ) -> ql.FixedRateBond:
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

        Returns:
            ql.FixedRateBond: The built fixed rate bond object.
        """

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

        bond = ql.FixedRateBond(
            settlement_days, face_value, schedule, coupons, day_count
        )

        return bond

    def bond_payment_schedule(self, bond: ql.Bond):
        """
        Generates the payment schedule for a bond.

        Args:
            bond (ql.Bond): The bond object.

        Returns:
            list: A list of tuples representing the payment schedule. Each tuple contains the payment date and amount.
        """
        payment_schedule = [(cf.date(), cf.amount()) for cf in bond.cashflows()]
        return payment_schedule

    def bond_value_fixed_forward_rate(
        self,
        bond: ql.Bond,
        reference_date: ql.Date,
        fixed_forward_rate: float,
        compounding: ql.Compounded | ql.Continuous,
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
            bond.dayCounter(),
            compounding,
            comp_frequency,
        )
        bond_engine = ql.DiscountingBondEngine(ql.YieldTermStructureHandle(yield_curve))

        bond.setPricingEngine(bond_engine)

        ql.Settings.instance().evaluationDate = reference_date

        npv = bond.NPV()
        clean_price = bond.cleanPrice()
        dirty_price = bond.dirtyPrice()
        accrued_interest = bond.accruedAmount()

        return npv, clean_price, dirty_price, accrued_interest
