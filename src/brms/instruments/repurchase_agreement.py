"""Define the RepurchaseAgreement class representing repo instruments."""

from typing import TYPE_CHECKING

from brms.instruments.base import Instrument
from brms.instruments.registry import OffBalanceSheetInstrumentRegistry

if TYPE_CHECKING:
    from brms.instruments.visitors import Visitor


class RepurchaseAgreement(Instrument):
    """A class to represent repo instruments."""

    def accept(self, visitor: "Visitor") -> None:
        """Accept a visitor."""
        raise NotImplementedError


OffBalanceSheetInstrumentRegistry.register(RepurchaseAgreement)
