"""The standardised approach, set out in OPE25.

To calculate operational RWA.
"""

from brms.metrics.base import RWAApproach
from brms.models.bank import Bank
from brms.models.scenario import ScenarioManager


class StandardisedApproach(RWAApproach):
    """The standardised approach for calculating operational RWA."""

    def compute_rwa(self, bank: Bank, scenario_manager: ScenarioManager, verbose: bool = False) -> float:
        """Compute the Risk-Weighted Assets (RWA) for a given bank and scenario."""
        raise NotImplementedError
