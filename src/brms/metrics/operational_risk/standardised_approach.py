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
        return sum(
            [
                ILDCCalculator.compute(bank, date, scenario_manager),
                SCCalculator.compute(bank, date, scenario_manager),
                FCCalculator.compute(bank, date, scenario_manager),
            ],
        )

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
        # Loss Component (LC)
        lc = LCCalculator.compute(bank, date, scenario_manager)
        # ILM
        return math.log(math.e - 1 + (lc / bic) ** 0.8)


class ILDCCalculator:
    """Calculator for the Interest, Leases, and Dividend Component (ILDC)."""

    @staticmethod
    def compute(bank: Bank, date: datetime.date, scenario_manager: ScenarioManager) -> float:
        """Compute the Interest, Leases, and Dividend Component (ILDC).

        ILDC is the sum of the following two:
        1. the minimum of
            - 3yr_avg(abs(interest income - interest expense))
            - 3yr_avg(interest earning assets) * 2.25%
        2. 3yr_avg(dividend income)
        """
        return 0.0


class SCCalculator:
    """Calculator for the Services Component (SC)."""

    @staticmethod
    def compute(bank: Bank, date: datetime.date, scenario_manager: ScenarioManager) -> float:
        """Compute the Services Component (SC).

        SC is the sum of the following two:
        1. the maximum of
            - 3yr_avg(other operating income)
            - 3yr_avg(other operating expense)
        2. the maximum of
            - 3yr_avg(fee income)
            - 3yr_avg(fee expense)
        """
        return 0.0


class FCCalculator:
    """Calculator for the Financial Component (FC)."""

    @staticmethod
    def compute(bank: Bank, date: datetime.date, scenario_manager: ScenarioManager) -> float:
        """Compute the Financial Component (FC).

        FC is the sum of the following two:
        1. 3yr_avg(abs(net P&L trading book))
        1. 3yr_avg(abs(net P&L banking book))
        """
        return 0.0


class LCCalculator:
    """Calculator for the Loss Component (LC)."""

    @staticmethod
    def compute(bank: Bank, date: datetime.date, scenario_manager: ScenarioManager) -> float:
        """Compute the Loss Component (LC).

        LC is equal to 15 times average annual operational risk losses incurred over the previous 10 years
        """
        average_annual_operational_risk_losses = 10000  # FIXME: compute average over the previous 10 years
        return 15 * average_annual_operational_risk_losses
