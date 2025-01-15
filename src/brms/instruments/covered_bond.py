"""Define the CoveredBond class representing covered bond instruments."""

from typing import TYPE_CHECKING

from brms.instruments.base import Instrument

if TYPE_CHECKING:
    from brms.instruments.visitor import Visitor


class CoveredBond(Instrument):
    """A class to represent covered bond instruments."""

    def accept(self, visitor: "Visitor") -> None:
        """Accept a visitor."""
        visitor.visit_covered_bond(self)
