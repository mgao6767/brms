"""Benchmark enums and QuantLib IborIndex subclass for variable-rate instruments."""

from __future__ import annotations

from enum import Enum

import QuantLib as ql  # noqa: N813


class BenchmarkFamily(Enum):
    """Benchmark rate families supported by VariableRateLoan."""

    PRIME = "prime"


class PrincipalRepaymentMode(Enum):
    """How principal is repaid over the loan's life."""

    BULLET = "bullet"
    SINKING = "sinking"


class PrimeIndex(ql.IborIndex):
    """U.S. Bank Prime Loan Rate modelled as a QuantLib IborIndex.

    Prime is not an IBOR in the textbook sense, but QL's IborIndex machinery
    provides exactly what we need: a named benchmark with fixing/computation
    conventions and a fixing history that FloatingRateBond coupons can read.

    Conventions:
        family name             USDPrime
        tenor                   1M (default; bond schedule controls actual reset)
        fixing days             0 (same-day fixing)
        fixing calendar         U.S. Federal Reserve business days
        business-day convention ModifiedFollowing
        day counter             Actual/365 Fixed
    """

    _DEFAULT_TENOR = ql.Period(1, ql.Months)

    def __init__(
        self,
        tenor: ql.Period | None = None,
        forwarding: ql.YieldTermStructureHandle | None = None,
    ) -> None:
        """Initialise the Prime index with optional tenor and forwarding curve."""
        end_of_month = False
        super().__init__(
            "USDPrime",
            tenor or self._DEFAULT_TENOR,
            0,
            ql.USDCurrency(),
            ql.UnitedStates(ql.UnitedStates.FederalReserve),
            ql.ModifiedFollowing,
            end_of_month,
            ql.Actual365Fixed(),
            forwarding or ql.YieldTermStructureHandle(),
        )
