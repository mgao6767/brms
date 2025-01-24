import datetime
from typing import ClassVar

import numpy as np
import pandas as pd
import QuantLib as ql
from dateutil.relativedelta import relativedelta


class YieldCurveService:
    """Service to convert par yields into zero yield curves using QuantLib."""

    MATURITY_MAPPING: ClassVar[dict] = {
        "1 Mo": ql.Period(1, ql.Months),
        "2 Mo": ql.Period(2, ql.Months),
        "3 Mo": ql.Period(3, ql.Months),
        "4 Mo": ql.Period(4, ql.Months),
        "6 Mo": ql.Period(6, ql.Months),
        "1 Yr": ql.Period(1, ql.Years),
        "2 Yr": ql.Period(2, ql.Years),
        "3 Yr": ql.Period(3, ql.Years),
        "5 Yr": ql.Period(5, ql.Years),
        "7 Yr": ql.Period(7, ql.Years),
        "10 Yr": ql.Period(10, ql.Years),
        "20 Yr": ql.Period(20, ql.Years),
        "30 Yr": ql.Period(30, ql.Years),
    }

    @staticmethod
    def build_yield_curve(ref_date: datetime.date, maturity_labels: list, rates: list) -> ql.YieldTermStructure:
        """Construct a QuantLib yield curve from provided maturity labels and rates.

        :param ref_date: Reference date (Python `datetime.date`)
        :param maturity_labels: List of column names corresponding to maturities (e.g., ["1 Mo", "2 Yr"])
        :param rates: List of yield values corresponding to the maturities (in percentage, e.g., [2.5, 3.0, 3.5])
        :return: QuantLib Piecewise Log-Cubic Discount yield curve
        """
        if len(maturity_labels) == 0 or len(rates) == 0:
            return None

        # Convert reference date to QuantLib Date
        ql_ref_date = ql.Date(ref_date.day, ref_date.month, ref_date.year)
        ql.Settings.instance().evaluationDate = ql_ref_date

        calendar = ql.UnitedStates(ql.UnitedStates.NYSE)
        business_convention = ql.Following
        end_of_month = False
        day_count = ql.ActualActual(ql.ActualActual.ISDA)

        # Separate short-term zero-coupon bonds from long-term coupon bonds
        zcb_data = []  # Zero-coupon bond data (≤1 year)
        coupon_bond_data = []  # Coupon bond data (>1 year)

        # Define threshold for ZCBs (1 year + 1 week)
        one_year_later = ref_date + relativedelta(years=1, weeks=1)

        for label, rate in zip(maturity_labels, rates, strict=True):
            if label not in YieldCurveService.MATURITY_MAPPING:
                raise ValueError(f"Unknown maturity label: {label}")

            if rate is None or np.isnan(rate):  # Skip missing rates
                continue

            # Convert rate from percentage to decimal (e.g., 2.5% → 0.025)
            rate = float(rate) / 100.0

            # Compute maturity date
            maturity_period = YieldCurveService.MATURITY_MAPPING[label]
            maturity_date = ql_ref_date + maturity_period

            if maturity_date < ql.Date(one_year_later.day, one_year_later.month, one_year_later.year):
                zcb_data.append((maturity_date, rate))
            else:
                coupon_bond_data.append((maturity_date, rate, 100.0))  # Assuming price 100

        # Create deposit rate helpers for short-term zero-coupon bonds
        zcb_helpers = [
            ql.DepositRateHelper(
                ql.QuoteHandle(ql.SimpleQuote(rate)),
                ql.Period(maturity_date - ql_ref_date, ql.Days),
                0,  # settlement days
                calendar,
                business_convention,
                end_of_month,
                day_count,
            )
            for maturity_date, rate in zcb_data
        ]

        # Create fixed-rate bond helpers for long-term coupon bonds
        bond_helpers = []
        for maturity_date, coupon_rate, price in coupon_bond_data:
            schedule = ql.Schedule(
                ql_ref_date,
                maturity_date,
                ql.Period(ql.Semiannual),
                calendar,
                business_convention,
                business_convention,
                ql.DateGeneration.Backward,
                end_of_month,
            )
            bond_helpers.append(
                ql.FixedRateBondHelper(
                    ql.QuoteHandle(ql.SimpleQuote(price)),
                    0,  # settlement days
                    100.0,  # face value
                    schedule,
                    [coupon_rate],
                    day_count,
                )
            )

        # Combine rate helpers
        rate_helpers = zcb_helpers + bond_helpers

        # Build the yield curve using a Piecewise Log-Cubic Discount
        yield_curve = ql.PiecewiseLogCubicDiscount(ql_ref_date, rate_helpers, day_count)
        yield_curve.enableExtrapolation()

        return yield_curve

    @classmethod
    def build_yield_curve_from_df(cls, df: pd.DataFrame, date: datetime.date) -> ql.YieldTermStructure:
        """Construct a QuantLib yield curve from a DataFrame and a specific date.

        :param df: DataFrame containing yield data with a 'date' column and maturity columns
        :param date: Specific date to extract the yield data
        :return: QuantLib YieldTermStructure
        """
        row = df[df["date"].dt.date == date]
        if row.empty:
            raise ValueError(f"No data available for the date: {date}")

        maturity_labels = [col for col in df.columns if col != "date"]
        rates = [row.iloc[0][col] for col in maturity_labels]
        return cls.build_yield_curve(date, maturity_labels, rates)
