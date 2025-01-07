"""The standardised approach, set out in CRE20 to CRE22.

To calculate credit RWA for banking book exposures.
"""

from brms.metrics.base import RWAApproach
from brms.models.bank import Bank
from brms.models.scenario import ScenarioManager


class StandardisedApproach(RWAApproach):
    """The standardised approach for calculating credit RWA."""

    def compute_rwa(self, bank: Bank, scenario_manager: ScenarioManager) -> float:
        """Compute the Risk-Weighted Assets (RWA) for a given bank and scenario."""
        self.bank = bank
        self.scenario_manager = scenario_manager

        rwa = 0.0
        rwa += self._compute_sovereign_exposures()
        rwa += self._compute_PSE_exposures()
        rwa += self._compute_MDB_exposures()
        rwa += self._compute_bank_exposures()
        rwa += self._compute_covered_bonds_exposures()
        rwa += self._compute_securities_firms_exposures()
        rwa += self._compute_corporate_exposures()
        rwa += self._compute_subordinated_debt_exposures()
        rwa += self._compute_retail_exposures()
        rwa += self._compute_real_estate_exposures()
        rwa += self._compute_currency_mismatch_exposures()
        rwa += self._compute_off_balance_sheet_items()
        rwa += self._compute_counterparty_credit_risk_exposures()
        rwa += self._compute_credit_derivatives_exposures()
        rwa += self._compute_defaulted_exposures()
        rwa += self._compute_other_assets_exposures()
        return rwa

    def _compute_sovereign_exposures(self) -> float:
        """Compute the RWA for sovereign exposures."""
        raise NotImplementedError

    def _compute_PSE_exposures(self) -> float:
        """Compute the RWA for PSE exposures."""
        raise NotImplementedError

    def _compute_MDB_exposures(self) -> float:
        """Compute the RWA for MDB exposures."""
        raise NotImplementedError

    def _compute_bank_exposures(self) -> float:
        """Compute the RWA for bank exposures."""
        raise NotImplementedError

    def _compute_covered_bonds_exposures(self) -> float:
        """Compute the RWA for covered bonds exposures."""
        raise NotImplementedError

    def _compute_securities_firms_exposures(self) -> float:
        """Compute the RWA for securities firms and other financial institutions exposures."""
        raise NotImplementedError

    def _compute_corporate_exposures(self) -> float:
        """Compute the RWA for corporate exposures."""
        raise NotImplementedError

    def _compute_subordinated_debt_exposures(self) -> float:
        """Compute the RWA for subordinated debt, equity and other capital instruments exposures."""
        raise NotImplementedError

    def _compute_retail_exposures(self) -> float:
        """Compute the RWA for retail exposures."""
        raise NotImplementedError

    def _compute_real_estate_exposures(self) -> float:
        """Compute the RWA for real estate exposures."""
        raise NotImplementedError

    def _compute_currency_mismatch_exposures(self) -> float:
        """Compute the RWA for risk weight multiplier to certain exposures with currency mismatch."""
        raise NotImplementedError

    def _compute_off_balance_sheet_items(self) -> float:
        """Compute the RWA for off-balance sheet items."""
        raise NotImplementedError

    def _compute_counterparty_credit_risk_exposures(self) -> float:
        """Compute the RWA for exposures that give rise to counterparty credit risk."""
        raise NotImplementedError

    def _compute_credit_derivatives_exposures(self) -> float:
        """Compute the RWA for credit derivatives."""
        raise NotImplementedError

    def _compute_defaulted_exposures(self) -> float:
        """Compute the RWA for defaulted exposures."""
        raise NotImplementedError

    def _compute_other_assets_exposures(self) -> float:
        """Compute the RWA for other assets."""
        raise NotImplementedError
