"""The standardised approach, set out in CRE20 to CRE22.

To calculate credit RWA for banking book exposures.
"""

from collections.abc import Iterable
from typing import ClassVar

from brms.instruments.base import CreditRating, Instrument, Issuer
from brms.metrics.base import RWAApproach
from brms.models.bank import Bank
from brms.models.scenario import ScenarioManager


class StandardisedApproach(RWAApproach):
    """The standardised approach for calculating credit RWA."""

    def compute_rwa(self, bank: Bank, scenario_manager: ScenarioManager) -> float:
        """Compute the Risk-Weighted Assets (RWA) for a given bank and scenario."""
        rwa = 0.0
        rwa += self._compute_sovereign_exposures(bank, scenario_manager)
        rwa += self._compute_PSE_exposures(bank, scenario_manager)
        rwa += self._compute_MDB_exposures(bank, scenario_manager)
        rwa += self._compute_bank_exposures(bank, scenario_manager)
        rwa += self._compute_covered_bonds_exposures(bank, scenario_manager)
        rwa += self._compute_securities_firms_exposures(bank, scenario_manager)
        rwa += self._compute_corporate_exposures(bank, scenario_manager)
        rwa += self._compute_subordinated_debt_exposures(bank, scenario_manager)
        rwa += self._compute_retail_exposures(bank, scenario_manager)
        rwa += self._compute_real_estate_exposures(bank, scenario_manager)
        rwa += self._compute_currency_mismatch_exposures(bank, scenario_manager)
        rwa += self._compute_off_balance_sheet_items(bank, scenario_manager)
        rwa += self._compute_counterparty_credit_risk_exposures(bank, scenario_manager)
        rwa += self._compute_credit_derivatives_exposures(bank, scenario_manager)
        rwa += self._compute_defaulted_exposures(bank, scenario_manager)
        rwa += self._compute_other_assets_exposures(bank, scenario_manager)
        return rwa

    def _compute_rwa(self, risk_table: type["RiskWeightTable"], instruments: Iterable[Instrument]) -> float:
        total_rwa = 0.0
        for instrument in instruments:
            total_rwa += risk_table.get_risk_weight(instrument.issuer) * instrument.value
        return total_rwa

    def _compute_sovereign_exposures(self, bank: Bank, scenario_manager: ScenarioManager) -> float:
        """Compute the RWA for sovereign exposures.

        TODO: An alternative to use country risk scores by Export Credit Agencies (ECAs), see CRE20.9.
        """
        return self._compute_rwa(
            RiskWeightTableForSovereignExposures,
            (instrument for instrument in bank.banking_book_assets() if instrument.issuer.is_sovereign()),
        )

    def _compute_PSE_exposures(self, bank: Bank, scenario_manager: ScenarioManager) -> float:
        """Compute the RWA for PSE exposures.

        TODO: An alternative to use the external ratings of sovereign, see CRE20.11.
        """
        return self._compute_rwa(
            RiskWeightTableForPSEBasedOnExternalRatingOfPSE,
            (instrument for instrument in bank.banking_book_assets() if instrument.issuer.is_PSE()),
        )

    def _compute_MDB_exposures(self, bank: Bank, scenario_manager: ScenarioManager) -> float:
        """Compute the RWA for MDB exposures."""
        return self._compute_rwa(
            RiskWeightTableForMDBExposures,
            (instrument for instrument in bank.banking_book_assets() if instrument.issuer.is_MDB()),
        )

    def _compute_bank_exposures(self, bank: Bank, scenario_manager: ScenarioManager) -> float:
        """Compute the RWA for bank exposures."""
        raise NotImplementedError

    def _compute_covered_bonds_exposures(self, bank: Bank, scenario_manager: ScenarioManager) -> float:
        """Compute the RWA for covered bonds exposures."""
        raise NotImplementedError

    def _compute_securities_firms_exposures(self, bank: Bank, scenario_manager: ScenarioManager) -> float:
        """Compute the RWA for securities firms and other financial institutions exposures."""
        raise NotImplementedError

    def _compute_corporate_exposures(self, bank: Bank, scenario_manager: ScenarioManager) -> float:
        """Compute the RWA for corporate exposures."""
        raise NotImplementedError

    def _compute_subordinated_debt_exposures(self, bank: Bank, scenario_manager: ScenarioManager) -> float:
        """Compute the RWA for subordinated debt, equity and other capital instruments exposures."""
        raise NotImplementedError

    def _compute_retail_exposures(self, bank: Bank, scenario_manager: ScenarioManager) -> float:
        """Compute the RWA for retail exposures."""
        raise NotImplementedError

    def _compute_real_estate_exposures(self, bank: Bank, scenario_manager: ScenarioManager) -> float:
        """Compute the RWA for real estate exposures."""
        raise NotImplementedError

    def _compute_currency_mismatch_exposures(self, bank: Bank, scenario_manager: ScenarioManager) -> float:
        """Compute the RWA for risk weight multiplier to certain exposures with currency mismatch."""
        raise NotImplementedError

    def _compute_off_balance_sheet_items(self, bank: Bank, scenario_manager: ScenarioManager) -> float:
        """Compute the RWA for off-balance sheet items."""
        raise NotImplementedError

    def _compute_counterparty_credit_risk_exposures(self, bank: Bank, scenario_manager: ScenarioManager) -> float:
        """Compute the RWA for exposures that give rise to counterparty credit risk."""
        raise NotImplementedError

    def _compute_credit_derivatives_exposures(self, bank: Bank, scenario_manager: ScenarioManager) -> float:
        """Compute the RWA for credit derivatives."""
        raise NotImplementedError

    def _compute_defaulted_exposures(self, bank: Bank, scenario_manager: ScenarioManager) -> float:
        """Compute the RWA for defaulted exposures."""
        raise NotImplementedError

    def _compute_other_assets_exposures(self, bank: Bank, scenario_manager: ScenarioManager) -> float:
        """Compute the RWA for other assets."""
        raise NotImplementedError


class RiskWeightTable:
    """Base class for risk weight tables."""

    _risk_weight_table: ClassVar[dict[tuple[CreditRating, CreditRating], float]] = {}

    @classmethod
    def get_risk_weight(cls, issuer: Issuer) -> float:
        """Get the risk weight for a given issuer."""
        rating = issuer.credit_rating
        for rating_range, risk_weight in cls._risk_weight_table.items():
            if rating_range[0] >= rating >= rating_range[1]:
                return risk_weight
        error_message = f"Invalid rating: {rating}"
        raise ValueError(error_message)


class RiskWeightTableForSovereignExposures(RiskWeightTable):
    """Class to represent the risk weight table for sovereigns and central banks.

    This is Table 1 of CRE20.7.
    """

    _risk_weight_table: ClassVar[dict[tuple[CreditRating, CreditRating], float]] = {
        (CreditRating.AAA, CreditRating.AA_MINUS): 0.0,  # AAA to AA-: 0% risk weight
        (CreditRating.A_PLUS, CreditRating.A_MINUS): 0.2,  # A+ to A-: 20% risk weight
        (CreditRating.BBB_PLUS, CreditRating.BBB_MINUS): 0.5,  # BBB+ to BBB-: 50% risk weight
        (CreditRating.BB_PLUS, CreditRating.B_MINUS): 1.0,  # BB+ to B-: 100% risk weight
        (CreditRating.B_PLUS, CreditRating.D): 1.5,  # B+ to D: 150% risk weight
        (CreditRating.UNRATED, CreditRating.UNRATED): 1.0,  # Unrated: 100% risk weight
    }


class RiskWeightTableForPSEBasedOnExternalRatingOfSovereign(RiskWeightTable):
    """Class to represent the risk weight table for domestic PSEs based on external ratings of sovereign.

    This is Table 3 of CRE20.11.
    """

    _risk_weight_table: ClassVar[dict[tuple[CreditRating, CreditRating], float]] = {
        (CreditRating.AAA, CreditRating.AA_MINUS): 0.2,
        (CreditRating.A_PLUS, CreditRating.A_MINUS): 0.5,
        (CreditRating.BBB_PLUS, CreditRating.BBB_MINUS): 1.0,
        (CreditRating.BB_PLUS, CreditRating.B_MINUS): 1.0,
        (CreditRating.B_PLUS, CreditRating.D): 1.5,
        (CreditRating.UNRATED, CreditRating.UNRATED): 1.0,
    }


class RiskWeightTableForPSEBasedOnExternalRatingOfPSE(RiskWeightTable):
    """Class to represent the risk weight table for domestic PSEs based on external ratings of PSE.

    This is Table 4 of CRE20.11.
    """

    _risk_weight_table: ClassVar[dict[tuple[CreditRating, CreditRating], float]] = {
        (CreditRating.AAA, CreditRating.AA_MINUS): 0.2,
        (CreditRating.A_PLUS, CreditRating.A_MINUS): 0.5,
        (CreditRating.BBB_PLUS, CreditRating.BBB_MINUS): 0.5,
        (CreditRating.BB_PLUS, CreditRating.B_MINUS): 1.0,
        (CreditRating.B_PLUS, CreditRating.D): 1.5,
        (CreditRating.UNRATED, CreditRating.UNRATED): 0.5,
    }


class RiskWeightTableForMDBExposures(RiskWeightTable):
    """Class to represent the risk weight table for multilateral development banks (MDBs).

    This is Table 5 of CRE20.15.
    MDBs with a zero risk weight are listed in footnote 8 of CRE20.14.
    """

    _risk_weight_table: ClassVar[dict[tuple[CreditRating, CreditRating], float]] = {
        (CreditRating.AAA, CreditRating.AA_MINUS): 0.2,
        (CreditRating.A_PLUS, CreditRating.A_MINUS): 0.3,
        (CreditRating.BBB_PLUS, CreditRating.BBB_MINUS): 0.5,
        (CreditRating.BB_PLUS, CreditRating.B_MINUS): 1.0,
        (CreditRating.B_PLUS, CreditRating.D): 1.5,
        (CreditRating.UNRATED, CreditRating.UNRATED): 0.5,
    }

    _mdb_with_zero_risk_weight: ClassVar[list[str]] = [
        "International Bank for Reconstruction and Development",
        "International Finance Corporation",
        "Multilateral Investment Guarantee Agency",
        "International Development Association",
        "Asian Development Bank",
        "African Development Bank",
        "European Bank for Reconstruction and Development",
        "Inter-American Development Bank",
        "European Investment Bank",
        "European Investment Fund",
        "Nordic Investment Bank",
        "Caribbean Development Bank",
        "Islamic Development Bank",
        "Council of Europe Development Bank",
        "International Finance Facility for Immunization",
        "Asian Infrastructure Investment Bank",
    ]

    @classmethod
    def get_risk_weight(cls, issuer: Issuer) -> float:
        """Get the risk weight for a given issuer."""
        risk_weight = super().get_risk_weight(issuer)
        if issuer.name in cls._mdb_with_zero_risk_weight:
            risk_weight = 0
        return risk_weight
