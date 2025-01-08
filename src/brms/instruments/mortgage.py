"""Mortgages."""

from brms.instruments.amortizing_fixed_rate_loan import AmortizingFixedRateLoan
from brms.instruments.registry import (
    CorporateInstrumentRegistry,
    MortgageInstrumentRegistry,
    RealEstateInstrumentRegistry,
    RetailInstrumentRegistry,
)


class Mortgage(AmortizingFixedRateLoan):
    """Base class for mortgages with a fixed interest rate."""


class ResidentialMortgage(Mortgage):
    """Represents a residential mortgage with a fixed interest rate."""


class CommercialMortgage(Mortgage):
    """Represents a commercial mortgage with a fixed interest rate."""


MortgageInstrumentRegistry.register(ResidentialMortgage)
MortgageInstrumentRegistry.register(CommercialMortgage)

RealEstateInstrumentRegistry.register(ResidentialMortgage)
RealEstateInstrumentRegistry.register(CommercialMortgage)

RetailInstrumentRegistry.register(ResidentialMortgage)
CorporateInstrumentRegistry.register(CommercialMortgage)
