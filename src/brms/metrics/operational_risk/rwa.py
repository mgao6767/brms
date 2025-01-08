"""Module defining classes for calculating Operational Risk Weighted Assets (RWA)."""

from brms.metrics.base import RWAApproach, RWAComponent
from brms.metrics.operational_risk import StandardisedApproach
from brms.models.bank import Bank
from brms.models.scenario import ScenarioManager


class OpertionalRWA(RWAComponent):
    """Operational RWA."""

    @classmethod
    def allowed_approaches(cls) -> list[type[RWAApproach]]:
        """Return a list of allowed RWA approaches for Operational Risk."""
        return [StandardisedApproach]


class RWAOperationalRisk:
    """Class for calculating Operational Risk Weighted Assets (RWA)."""

    def __init__(self) -> None:
        """Initialize the RWAOperationalRisk class."""
        self.rwa_operational_risk = OpertionalRWA()

        self._rwa_components: list[RWAComponent] = [self.rwa_operational_risk]

        self.set_approach_for_operational_rwa(StandardisedApproach())

    def compute_rwa(self, bank: Bank, scenario_manager: ScenarioManager) -> float:
        """Compute the total Operational RWA for the bank under the given scenario."""
        return sum(component.compute_rwa(bank, scenario_manager) for component in self._rwa_components)

    def set_approach_for_operational_rwa(self, approach: RWAApproach) -> None:
        """Set the approach for operational RWA."""
        self.rwa_operational_risk.approach = approach
