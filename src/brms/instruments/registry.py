"""Module for registering and checking instrument types."""

from typing import ClassVar

from brms.instruments.base import Instrument


class InstrumentRegistry:
    """Registry for instrument types."""

    _instrument_types: ClassVar[set[type]] = set()

    @classmethod
    def register(cls, instrument_type: type) -> None:
        """Register a new instrument type."""
        cls._instrument_types.add(instrument_type)

    @classmethod
    def has_instrument(cls, instrument: Instrument) -> bool:
        """Check if the registry contains the instrument."""
        return isinstance(instrument, tuple(cls._instrument_types))


class RealEstateInstrumentRegistry(InstrumentRegistry):
    """Registry for real estate instrument types."""

    _instrument_types: ClassVar[set[type]] = set()


class RetailInstrumentRegistry(InstrumentRegistry):
    """Registry for retail instrument types."""

    _instrument_types: ClassVar[set[type]] = set()


class TreasuryInstrumentRegistry(InstrumentRegistry):
    """Registry for treasury instrument types."""

    _instrument_types: ClassVar[set[type]] = set()


class PSEInstrumentRegistry(InstrumentRegistry):
    """Registry for PSE instrument types."""

    _instrument_types: ClassVar[set[type]] = set()


class MDBInstrumentRegistry(InstrumentRegistry):
    """Registry for MDB instrument types."""

    _instrument_types: ClassVar[set[type]] = set()


class CorporateInstrumentRegistry(InstrumentRegistry):
    """Registry for corporate instrument types."""

    _instrument_types: ClassVar[set[type]] = set()


class OffBalanceSheetInstrumentRegistry(InstrumentRegistry):
    """Registry for off-balance-sheet instrument types."""

    _instrument_types: ClassVar[set[type]] = set()


class LoanInstrumentRegistry(InstrumentRegistry):
    """Registry for loan instrument types."""

    _instrument_types: ClassVar[set[type]] = set()


class MortgageInstrumentRegistry(InstrumentRegistry):
    """Registry for mortgage instrument types."""

    _instrument_types: ClassVar[set[type]] = set()
