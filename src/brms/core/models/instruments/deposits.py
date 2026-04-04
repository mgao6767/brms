"""Deposit instrument classes for the core domain model."""

from brms.core.models.instruments.base import Instrument


class Cash(Instrument):
    """A class to represent cash."""

    def __init__(self, value: float = 0.0) -> None:
        """Initialize cash with an optional value.

        Args:
            value (float): The value of the cash. Defaults to 0.0.

        """
        super().__init__(name="Cash")
        self.value = value

    def accept(self, visitor: object) -> None:
        """Accept a visitor."""
        visitor.visit_cash(self)  # type: ignore[union-attr]


class Deposit(Instrument):
    """A class to represent customer deposit."""

    def __init__(self, *, name: str = "Deposit", value: float = 0.0) -> None:
        """Initialize a deposit with an optional name and value.

        Args:
            name (str): The name of the deposit. Defaults to "Deposit".
            value (float): The value of the deposit. Defaults to 0.0.

        """
        super().__init__(name=name)
        self.value = value

    def accept(self, visitor: object) -> None:
        """Accept a visitor."""
        visitor.visit_deposit(self)  # type: ignore[union-attr]
