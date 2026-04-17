"""Registry for financial instrument types to support deserialization."""

from collections.abc import Callable
from typing import ClassVar

from brms.core.models.instruments.base import Instrument


class InstrumentRegistry:
    """Registry mapping type identifiers to instrument classes or factory callables.

    Allows decoupled deserialization: callers register concrete instrument types
    by a string key, then create instances by key without hard-coded imports.
    """

    def __init__(self) -> None:
        """Initialize an empty registry."""
        self._registry: dict[str, type[Instrument] | Callable[..., Instrument]] = {}

    def register(self, type_id: str, cls: type[Instrument] | Callable[..., Instrument]) -> None:
        """Register an instrument class or factory under the given type identifier.

        Args:
            type_id: A unique string key for the instrument type.
            cls: The concrete instrument class or a factory callable.

        """
        self._registry[type_id] = cls

    def create(self, type_id: str, **kwargs: object) -> Instrument:
        """Create an instrument instance for the given type identifier.

        Args:
            type_id: The string key previously registered via :meth:`register`.
            **kwargs: Keyword arguments forwarded to the instrument constructor.

        Returns:
            A new instance of the registered instrument class.

        Raises:
            KeyError: If *type_id* has not been registered.

        """
        cls = self._registry[type_id]
        return cls(**kwargs)


# ---------------------------------------------------------------------------
# Category registries used by risk-weight calculations (standardised approach)
# ---------------------------------------------------------------------------


class CategoryRegistry:
    """Registry that checks whether an instrument belongs to a category by type."""

    _instrument_types: ClassVar[set[type]] = set()

    @classmethod
    def register(cls, instrument_type: type) -> None:
        """Register a new instrument type in this category."""
        cls._instrument_types.add(instrument_type)

    @classmethod
    def has_instrument(cls, instrument: Instrument) -> bool:
        """Return True if *instrument* is an instance of a registered type."""
        return isinstance(instrument, tuple(cls._instrument_types))


class RealEstateInstrumentRegistry(CategoryRegistry):
    """Registry for real estate instrument types."""

    _instrument_types: ClassVar[set[type]] = set()


class RetailInstrumentRegistry(CategoryRegistry):
    """Registry for retail instrument types."""

    _instrument_types: ClassVar[set[type]] = set()


class TreasuryInstrumentRegistry(CategoryRegistry):
    """Registry for treasury instrument types."""

    _instrument_types: ClassVar[set[type]] = set()


class PSEInstrumentRegistry(CategoryRegistry):
    """Registry for PSE instrument types."""

    _instrument_types: ClassVar[set[type]] = set()


class MDBInstrumentRegistry(CategoryRegistry):
    """Registry for MDB instrument types."""

    _instrument_types: ClassVar[set[type]] = set()


class CorporateInstrumentRegistry(CategoryRegistry):
    """Registry for corporate instrument types."""

    _instrument_types: ClassVar[set[type]] = set()


class OffBalanceSheetInstrumentRegistry(CategoryRegistry):
    """Registry for off-balance-sheet instrument types."""

    _instrument_types: ClassVar[set[type]] = set()


class LoanInstrumentRegistry(CategoryRegistry):
    """Registry for loan instrument types."""

    _instrument_types: ClassVar[set[type]] = set()


class MortgageInstrumentRegistry(CategoryRegistry):
    """Registry for mortgage instrument types."""

    _instrument_types: ClassVar[set[type]] = set()
