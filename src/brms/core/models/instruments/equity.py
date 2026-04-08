"""Equity instrument classes for the core domain model."""

from __future__ import annotations

from typing import TYPE_CHECKING

from brms.core.enums import InstrumentType
from brms.core.models.instruments.base import Instrument

if TYPE_CHECKING:
    from brms.core.visitors.base import Visitor


class CommonEquity(Instrument):
    """A class to represent common equity instruments."""

    def __init__(self, *, name: str = "Common Equity") -> None:
        """Initialize common equity with an optional name.

        Args:
            name (str): The name of the equity instrument. Defaults to "Common Equity".

        """
        super().__init__(name=name)
        self.instrument_type = InstrumentType.COMMON_EQUITY

    def accept(self, visitor: Visitor) -> None:
        """Accept a visitor."""
        visitor.visit_common_equity(self)  # type: ignore[union-attr]
