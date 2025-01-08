"""The standardised approach, set out in OPE25.

To calculate operational RWA.
"""

import datetime
import math

from brms.metrics.base import RWAApproach
from brms.models.bank import Bank
from brms.models.scenario import ScenarioManager


class StandardisedApproach(RWAApproach):
    """The standardised approach for calculating operational RWA."""

    def compute_rwa(self, bank: Bank, date: datetime.date, scenario_manager: ScenarioManager) -> float:
        """Compute the Risk-Weighted Assets (RWA) for a given bank and scenario."""
        bi = self._compute_business_indicator(bank, date, scenario_manager)
        bic = self._compute_business_indicator_component(bi)
        ilm = self._compute_internal_loss_multiplier(bic, bank, date, scenario_manager)
        # Operational risk capital requirements (ORC) = BIC * ILM
        orc = bic * ilm
        # RWA for operational risk is 12.5 times ORC.
        return orc * 12.5

    def _compute_business_indicator(self, bank: Bank, date: datetime.date, scenario_manager: ScenarioManager) -> float:
        """Compute the Business Indicator (BI).

        It is a financial-statement-based proxy for operational risk.

        The BI comprises three components (see OPE25.3):
        1. the interest, leases and dividend component (ILDC);
        2. the services component (SC), and
        3. the financial component (FC).

        BI = ILDC + SC + FC
        """
        raise NotImplementedError

    def _compute_business_indicator_component(self, bi: float) -> float:
        """Compute the Business Indicator Component (BIC).

        It is calculated by multiplying the BI by a set of regulatory determined marginal coefficients (alpha).
        """
        bucket_1_upper_bound = 1_000_000_000
        bucket_2_upper_bound = 30_000_000_000
        alpha1 = 0.12
        alpha2 = 0.15
        alpha3 = 0.18

        if 0 < bi <= bucket_1_upper_bound:
            return bi * alpha1
        if bucket_1_upper_bound < bi <= bucket_2_upper_bound:
            return bucket_1_upper_bound * alpha1 + (bi - bucket_1_upper_bound) * alpha2
        return (
            bucket_1_upper_bound * alpha1
            + (bucket_2_upper_bound - bucket_1_upper_bound) * alpha2
            + (bi - bucket_2_upper_bound) * alpha3
        )

    def _compute_internal_loss_multiplier(
        self,
        bic: float,
        bank: Bank,
        date: datetime.date,
        scenario_manager: ScenarioManager,
    ) -> float:
        """Compute the Internal Loss Multiplier (ILM).

        It is a scaling factor that is based on a bank's average historical losses and the BIC.
        """
        average_annual_operational_risk_losses = 10000  # FIXME: compute average over the previous 10 years
        # Loss Component (LC)
        lc = 15 * average_annual_operational_risk_losses
        # ILM
        return math.log(math.e - 1 + (lc / bic) ** 0.8)
