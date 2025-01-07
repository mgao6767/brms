"""The standardised approach, set out in CRE20 to CRE22.

To calculate credit RWA for banking book exposures.
"""

from collections.abc import Callable, Iterable
from typing import ClassVar

from brms.instruments.base import CreditRating, Instrument
from brms.instruments.covered_bond import CoveredBond
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
            total_rwa += risk_table.get_risk_weight(instrument) * instrument.value
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

    def _compute_bank_exposures(
        self,
        bank: Bank,
        scenario_manager: ScenarioManager,
        instrument_filter: Callable | None = None,
    ) -> float:
        """Compute the RWA for bank exposures.

        Bank exposures will be risk-weighted based on the following hierarchy:
        1. External Credit Risk Assessment Approach (ECRA)
        2. Standardised Credit Risk Assessment Approach (SCRA)

        When the bank is not rated (by an eligible credit assessment institution (ECAI)), SCRA applies.
        """

        def issuer_is_bank(instrument: Instrument) -> bool:
            return instrument.issuer.is_bank()

        def instrument_is_short_term(instrument: Instrument) -> bool:
            # Exposures to banks with an original maturity of three months or less,
            # as well as exposures to banks that arise from the movement of goods across national borders
            # with an original maturity of six months or less can be assigned a risk weight that correspond to
            # the risk weights for short term exposures in Table 6.
            #
            # TODO: Check if instrument is short term.
            # Currently we assume no short-term exposure. The resulting RWA will be more conservative.
            return False

        _filter = instrument_filter or issuer_is_bank

        total_rwa = 0.0
        for instrument in bank.banking_book_assets():
            issuer = instrument.issuer
            if not _filter(instrument):
                continue
            if issuer.credit_rating > CreditRating.UNRATED:
                # Apply ECRA
                if instrument_is_short_term(instrument):
                    weight = RiskWeightTableForShortTermExposuresToBanks.get_risk_weight(instrument)
                else:
                    weight = RiskWeightTableForExposuresToBanks.get_risk_weight(instrument)
                total_rwa += instrument.value * weight
            else:
                # Apply SCRA
                raise NotImplementedError

        return total_rwa

    def _compute_covered_bonds_exposures(self, bank: Bank, scenario_manager: ScenarioManager) -> float:
        """Compute the RWA for covered bonds exposures.

        For covered bonds with issue-specific ratings, the risk weight is determined in Table 8.
        For unrated covered bonds, the risk weight is inferred from the issuer's ECRA or SCRA risk weight in Table 9.

        TODO: Address unrated covered bonds.
        TODO: Check if the covered bond is eligible based on CRE20.34 to CRE20.36.
        """
        return self._compute_rwa(
            RiskWeightTableForRatedCoveredBondExposures,
            (instrument for instrument in bank.banking_book_assets() if isinstance(instrument, CoveredBond)),
        )

    def _compute_securities_firms_exposures(self, bank: Bank, scenario_manager: ScenarioManager) -> float:
        """Compute the RWA for securities firms and other financial institutions exposures.

        Exposures to securities firms and other financial institutions will be treated as exposures to banks
        provided that these firms are subject to prudential standards and a level of supervision equivalent to
        those applied to banks (including capital and liquidity requirements).

        Exposures to all other securities firms and financial institutions will be treated as exposures to corporates.
        """

        def issuer_is_securities_firm(instrument: Instrument) -> bool:
            return instrument.issuer.is_securities_firm()

        return self._compute_bank_exposures(bank, scenario_manager, instrument_filter=issuer_is_securities_firm)

    def _compute_corporate_exposures(self, bank: Bank, scenario_manager: ScenarioManager) -> float:
        """Compute the RWA for corporate exposures.

        The corporate exposure class includes exposures to insurance companies and other financial corporates that
        do not meet the definitions of exposures to banks, or securities firms and other financial institutions,
        as determined in CRE20.16 and CRE20.40 respectively.
        The corporate exposure class does not include exposures to individuals.
        The corporate exposure class differentiates between the following subcategories:
        1. General corporate exposures;
        TODO 2. Specialised lending exposures, as defined in CRE20.48.
        """
        # TODO: Unrated SME and unrated "investment grade" corporate have different risk weights.
        return self._compute_rwa(
            RiskWeightTableForCorporateExposures,
            (instrument for instrument in bank.banking_book_assets() if instrument.issuer.is_corporate()),
        )

    def _compute_subordinated_debt_exposures(self, bank: Bank, scenario_manager: ScenarioManager) -> float:
        """Compute the RWA for subordinated debt, equity and other capital instruments exposures."""
        raise NotImplementedError

    def _compute_retail_exposures(self, bank: Bank, scenario_manager: ScenarioManager) -> float:
        """Compute the RWA for retail exposures.

        The risk weights that apply to exposures in the retail asset class are as follows:
        1. Regulatory retail exposures that do not arise from exposures to transactors (as defined in CRE20.66)
            will be risk weighted at 75%.
        2. Regulatory retail exposures that arise from exposures to transactors (as defined in CRE20.66)
            will be risk weighted at 45%.
        3. Other retail exposures will be risk weighted at 100%.

        Retail exposure class includes:
        1. exposures to an individual person or persons; and
        2. exposures to SMEs (as defined in CRE20.47) that meet the “regulatory retail” criteria set out in
            CRE20.65(1) to CRE20.65(3) below.

        "Regulatory retail" exposures are defined as retail exposures that meet ALL of the criteria listed below:
        1. Product criterion: the exposure takes the form of any of the following:
            - revolving credits and lines of credit (including credit cards, charge cards and overdrafts),
            - personal term loans and leases (eg instalment loans, auto loans and leases, student and educational loans,
                personal finance) and small business facilities and commitments.
            - Mortgage loans, derivatives and other securities are specifically **excluded** from this category.
        2. Low value of individual exposures: the maximum aggregated exposure to one counterparty cannot exceed an
            absolute threshold of €1 million.
        3. Granularity criterion: ...
        """

        def _filter(instrument: Instrument) -> bool:
            """Get qualifying instruments."""
            return instrument.issuer.is_individual() or instrument.issuer.is_SME()

        def is_regulatory_retail(instrument: Instrument, bank: Bank) -> bool:
            """TODO: Check if the exposure qualifies regulatory retail."""
            return False

        def is_transactor(instrument: Instrument, bank: Bank) -> bool:
            """TODO: Check if the obligator qualifies transactor."""
            return False

        def _get_risk_weight(instrument: Instrument) -> float:
            if is_regulatory_retail(instrument, bank):
                if not is_transactor(instrument, bank):
                    return 0.75
                return 0.45
            return 1.0

        total_rwa = 0.0
        for instrument in bank.banking_book_assets():
            if not _filter(instrument):
                continue
            total_rwa += instrument.value * _get_risk_weight(instrument)
        return total_rwa

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
    def get_risk_weight(cls, instrument: Instrument, use_issuer_rating: bool = True) -> float:
        """Get the risk weight."""
        rating = instrument.issuer.credit_rating if use_issuer_rating else instrument.credit_rating
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
    def get_risk_weight(cls, instrument: Instrument, use_issuer_rating: bool = True) -> float:
        """Get the risk weight for a given issuer."""
        risk_weight = super().get_risk_weight(instrument, use_issuer_rating)
        if instrument.issuer.name in cls._mdb_with_zero_risk_weight:
            risk_weight = 0
        return risk_weight


class RiskWeightTableForExposuresToBanks(RiskWeightTable):
    """Class to represent the risk weight table for exposures to banks.

    This is first panel of Table 6 of CRE20.18.
    """

    _risk_weight_table: ClassVar[dict[tuple[CreditRating, CreditRating], float]] = {
        (CreditRating.AAA, CreditRating.AA_MINUS): 0.2,
        (CreditRating.A_PLUS, CreditRating.A_MINUS): 0.3,
        (CreditRating.BBB_PLUS, CreditRating.BBB_MINUS): 0.5,
        (CreditRating.BB_PLUS, CreditRating.B_MINUS): 1.0,
        (CreditRating.B_PLUS, CreditRating.D): 1.5,
    }


class RiskWeightTableForShortTermExposuresToBanks(RiskWeightTable):
    """Class to represent the risk weight table for short-term exposures to banks.

    This is second panel of Table 6 of CRE20.18.
    """

    _risk_weight_table: ClassVar[dict[tuple[CreditRating, CreditRating], float]] = {
        (CreditRating.AAA, CreditRating.AA_MINUS): 0.2,
        (CreditRating.A_PLUS, CreditRating.A_MINUS): 0.2,
        (CreditRating.BBB_PLUS, CreditRating.BBB_MINUS): 0.2,
        (CreditRating.BB_PLUS, CreditRating.B_MINUS): 0.5,
        (CreditRating.B_PLUS, CreditRating.D): 1.5,
    }


class RiskWeightTableForRatedCoveredBondExposures(RiskWeightTable):
    """Class to represent the risk weight table for rated covered bond exposures.

    This is Table 8 of CRE20.38.
    """

    _risk_weight_table: ClassVar[dict[tuple[CreditRating, CreditRating], float]] = {
        (CreditRating.AAA, CreditRating.AA_MINUS): 0.1,
        (CreditRating.A_PLUS, CreditRating.A_MINUS): 0.2,
        (CreditRating.BBB_PLUS, CreditRating.BBB_MINUS): 0.2,
        (CreditRating.BB_PLUS, CreditRating.B_MINUS): 0.5,
        (CreditRating.B_PLUS, CreditRating.D): 1.0,
    }

    @classmethod
    def get_risk_weight(cls, instrument: Instrument, use_issuer_rating: bool = False) -> float:
        """Get the risk weight based on the instrument's credit rating."""
        risk_weight = super().get_risk_weight(instrument, use_issuer_rating)
        return risk_weight


class RiskWeightTableForCorporateExposures(RiskWeightTable):
    """Class to represent the risk weight table for exposures to corporate.

    This is Table 10 of CRE20.43.
    """

    _risk_weight_table: ClassVar[dict[tuple[CreditRating, CreditRating], float]] = {
        (CreditRating.AAA, CreditRating.AA_MINUS): 0.2,
        (CreditRating.A_PLUS, CreditRating.A_MINUS): 0.5,
        (CreditRating.BBB_PLUS, CreditRating.BBB_MINUS): 0.75,
        (CreditRating.BB_PLUS, CreditRating.B_MINUS): 1.0,
        (CreditRating.B_PLUS, CreditRating.D): 1.5,
        (CreditRating.UNRATED, CreditRating.UNRATED): 1.0,
    }
