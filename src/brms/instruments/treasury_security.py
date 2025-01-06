"""Treasury securities: Treasury Bills, Treasury Notes, and Treasury Bonds."""

from brms.instruments.base import Instrument
from brms.instruments.fixed_rate_bond import FixedRateBond


class TreasuryBill(Instrument):
    pass


class TreasuryNote(FixedRateBond):
    """Represents a Treasury Note with a fixed interest rate and maturity between one and ten years."""


class TreasuryBond(FixedRateBond):
    """Represents a Treasury Bond with a fixed interest rate and maturity greater than ten years."""
