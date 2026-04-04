"""Registry for financial instrument types to support deserialization."""

from brms.core.models.instruments.base import Instrument


class InstrumentRegistry:
    """Registry mapping type identifiers to instrument classes.

    Allows decoupled deserialization: callers register concrete instrument types
    by a string key, then create instances by key without hard-coded imports.
    """

    def __init__(self) -> None:
        """Initialize an empty registry."""
        self._registry: dict[str, type[Instrument]] = {}

    def register(self, type_id: str, cls: type[Instrument]) -> None:
        """Register an instrument class under the given type identifier.

        Args:
            type_id: A unique string key for the instrument type.
            cls: The concrete instrument class to register.

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
