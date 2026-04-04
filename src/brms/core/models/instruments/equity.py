"""Equity instrument classes for the core domain model."""

from brms.core.models.instruments.base import Instrument


class CommonEquity(Instrument):
    """A class to represent common equity instruments."""

    def __init__(self, *, name: str = "Common Equity", value: float = 0.0) -> None:
        """Initialize common equity with an optional name and value.

        Args:
            name (str): The name of the equity instrument. Defaults to "Common Equity".
            value (float): The value of the equity instrument. Defaults to 0.0.

        """
        super().__init__(name=name)
        self.value = value

    def accept(self, visitor: object) -> None:
        """Accept a visitor."""
        visitor.visit_common_equity(self)  # type: ignore[union-attr]
