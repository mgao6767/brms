"""Define the Commitment class representing commitments."""

from typing import TYPE_CHECKING

from brms.instruments.base import Instrument
from brms.instruments.registry import OffBalanceSheetInstrumentRegistry

if TYPE_CHECKING:
    from brms.instruments.visitors import Visitor


class Commitment(Instrument):
    """A class to represent commitments."""

    def accept(self, visitor: "Visitor") -> None:
        """Accept a visitor."""
        raise NotImplementedError


OffBalanceSheetInstrumentRegistry.register(Commitment)
