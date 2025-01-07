"""The Securitisation Standardised Approach (SEC-SA), set out in CRE40 to CRE45.

To calculate Credit RWA for securitisation exposures held in the banking book.
"""

from brms.metrics.base import RWAApproach
from brms.models.bank import Bank
from brms.models.scenario import ScenarioManager


class SecuritisationStandardisedApproach(RWAApproach):
    """SEC-SA for calculating credit RWA."""

    def compute_rwa(self, bank: Bank, scenario_manager: ScenarioManager) -> float:
        """Compute the Risk-Weighted Assets (RWA) for a given bank and scenario."""
        raise NotImplementedError
