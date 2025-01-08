"""Define the RepurchaseAgreement class representing repo instruments."""

from brms.instruments.base import Instrument
from brms.instruments.registry import OffBalanceSheetInstrumentRegistry
from brms.instruments.valuation import ValuationVisitor
from brms.models.scenario import Scenario


class RepurchaseAgreement(Instrument):
    """A class to represent repo instruments."""

    def accept(self, visitor: ValuationVisitor, scenario: Scenario) -> float:
        """Accept a valuation visitor to calculate the instrument's value."""
        # return visitor.value_repurchase_agreement(self, scenario)
        raise NotImplementedError


OffBalanceSheetInstrumentRegistry.register(RepurchaseAgreement)
