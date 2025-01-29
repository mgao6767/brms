"""Treasury securities: Treasury Bills, Treasury Notes, and Treasury Bonds."""

from brms.instruments.base import Instrument
from brms.instruments.fixed_rate_bond import FixedRateBond
from brms.instruments.registry import TreasuryInstrumentRegistry


class TreasuryBill(Instrument):
    pass


class TreasuryNote(FixedRateBond):
    """Represents a Treasury Note with a fixed interest rate and maturity between one and ten years."""

    instrument_type = "Treasury Note"


class TreasuryBond(FixedRateBond):
    """Represents a Treasury Bond with a fixed interest rate and maturity greater than ten years."""

    instrument_type = "Treasury Bond"


TreasuryInstrumentRegistry.register(TreasuryBill)
TreasuryInstrumentRegistry.register(TreasuryNote)
TreasuryInstrumentRegistry.register(TreasuryBond)
