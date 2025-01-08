"""The standardised approach, set out in CRE20 to CRE22.

To calculate credit RWA for banking book exposures.
"""

import datetime
from abc import ABC, abstractmethod
from collections.abc import Callable, Iterable
from typing import ClassVar

from brms.instruments.base import CreditRating, Instrument
from brms.instruments.cash import Cash
from brms.instruments.covered_bond import CoveredBond
from brms.instruments.registry import (
    CorporateInstrumentRegistry,
    LoanInstrumentRegistry,
    MDBInstrumentRegistry,
    PSEInstrumentRegistry,
    RealEstateInstrumentRegistry,
    RetailInstrumentRegistry,
    TreasuryInstrumentRegistry,
)
from brms.metrics.base import RWAApproach
from brms.models.bank import Bank
from brms.models.scenario import ScenarioManager


class ExposureChecker:
    """Class to check different types of exposures."""

    @staticmethod
    def is_real_estate_exposure(instrument: Instrument, bank: Bank) -> bool:
        """Check if the instrument is a real estate exposure."""
        return RealEstateInstrumentRegistry.has_instrument(instrument)

    @staticmethod
    def is_retail_exposure(instrument: Instrument, bank: Bank) -> bool:
        """Check if the exposure qualifies regulatory retail."""
        # Must not be real estate exposures
        if ExposureChecker.is_real_estate_exposure(instrument, bank):
            return False
        # Must be some kinds of retail instruments
        if not RetailInstrumentRegistry.has_instrument(instrument):
            return False
        # Must be from individuals or certain SMEs
        return instrument.issuer.is_individual() or instrument.issuer.is_SME()

    @staticmethod
    def is_sovereign_exposure(instrument: Instrument, bank: Bank) -> bool:
        """Check if the instrument qualifies sovereign or central bank exposure."""
        if TreasuryInstrumentRegistry.has_instrument(instrument):
            return True
        return instrument.issuer.is_sovereign()

    @staticmethod
    def is_PSE_exposure(instrument: Instrument, bank: Bank) -> bool:
        """Check if the instrument qualifies PSE exposure."""
        if PSEInstrumentRegistry.has_instrument(instrument):
            return True
        return instrument.issuer.is_PSE()

    @staticmethod
    def is_MDB_exposure(instrument: Instrument, bank: Bank) -> bool:
        """Check if the instrument qualifies MDB exposure."""
        if MDBInstrumentRegistry.has_instrument(instrument):
            return True
        return instrument.issuer.is_MDB()

    @staticmethod
    def is_covered_bond_exposure(instrument: Instrument, bank: Bank) -> bool:
        """Check if the instrument qualifies covered bond exposure."""
        return isinstance(instrument, CoveredBond)

    @staticmethod
    def is_corporate_exposure(instrument: Instrument, bank: Bank) -> bool:
        """Check if the instrument qualifies corporate exposure."""
        # Must not be real estate exposures
        if ExposureChecker.is_real_estate_exposure(instrument, bank):
            return False
        # Must be some kinds of corporate instruments
        if not CorporateInstrumentRegistry.has_instrument(instrument):
            return False
        # Must be from corporate
        return instrument.issuer.is_corporate()

    @staticmethod
    def is_bank_exposure(instrument: Instrument, bank: Bank) -> bool:
        """Check if the instrument qualifies bank exposure."""
        if not instrument.issuer.is_bank():
            return False
        # TODO: Should exclude subordinated debt on DIs.
        # TODO: Should be true for senior debt instruments too.
        return LoanInstrumentRegistry.has_instrument(instrument)

    @staticmethod
    def is_short_term_exposure(instrument: Instrument, bank: Bank) -> bool:
        """Check if the instrument qualifies short-term exposure."""
        return False  # TODO: check instrument maturity, which needs current scenario!

    @staticmethod
    def is_securities_firm_exposure(instrument: Instrument, bank: Bank) -> bool:
        """Check if the instrument qualifies securities firm exposure."""
        return instrument.issuer.is_securities_firm()

    @staticmethod
    def is_credit_derivative_exposure(instrument: Instrument, bank: Bank) -> bool:
        """Check if the instrument qualifies credit derivative exposure."""
        return False

    @staticmethod
    def is_defaulted_exposure(instrument: Instrument, bank: Bank) -> bool:
        """Check if the instrument qualifies defaulted exposure."""
        return False

    @staticmethod
    def is_cash_exposure(instrument: Instrument, bank: Bank) -> bool:
        """Check if the instrument is cash."""
        return isinstance(instrument, Cash)

    @staticmethod
    def is_other_exposure(instrument: Instrument, bank: Bank) -> bool:
        """Check if the instrument does not qualify all other exposures."""
        return not any(
            [
                ExposureChecker.is_real_estate_exposure(instrument, bank),
                ExposureChecker.is_retail_exposure(instrument, bank),
                ExposureChecker.is_sovereign_exposure(instrument, bank),
                ExposureChecker.is_PSE_exposure(instrument, bank),
                ExposureChecker.is_MDB_exposure(instrument, bank),
                ExposureChecker.is_covered_bond_exposure(instrument, bank),
                ExposureChecker.is_corporate_exposure(instrument, bank),
                ExposureChecker.is_bank_exposure(instrument, bank),
                ExposureChecker.is_securities_firm_exposure(instrument, bank),
                ExposureChecker.is_credit_derivative_exposure(instrument, bank),
                ExposureChecker.is_defaulted_exposure(instrument, bank),
            ],
        )


class StandardisedApproach(RWAApproach):
    """The standardised approach for calculating credit RWA."""

    def compute_rwa(
        self, bank: Bank, date: datetime.date, scenario_manager: ScenarioManager, verbose: bool = False
    ) -> float:
        """Compute the Risk-Weighted Assets (RWA) for a given bank and scenario."""
        rwa = 0.0
        exposures: list[tuple[str, Callable[[Bank, ScenarioManager], float]]] = [
            ("sovereign exposures", self._compute_sovereign_exposures),
            ("PSE exposures", self._compute_PSE_exposures),
            ("MDB exposures", self._compute_MDB_exposures),
            ("bank exposures", self._compute_bank_exposures),
            ("covered bonds exposures", self._compute_covered_bonds_exposures),
            ("securities firms exposures", self._compute_securities_firms_exposures),
            ("corporate exposures", self._compute_corporate_exposures),
            # ("subordinated debt exposures", self._compute_subordinated_debt_exposures),
            ("retail exposures", self._compute_retail_exposures),
            ("real estate exposures", self._compute_real_estate_exposures),
            # ("currency mismatch exposures", self._compute_currency_mismatch_exposures),
            # ("off-balance sheet items", self._compute_off_balance_sheet_items),
            ("counterparty credit risk exposures", self._compute_counterparty_credit_risk_exposures),
            # ("credit derivatives exposures", self._compute_credit_derivatives_exposures),
            # ("defaulted exposures", self._compute_defaulted_exposures),
            ("other assets exposures", self._compute_other_assets_exposures),
        ]

        for exposure_name, compute_func in exposures:
            exposure_rwa = compute_func(bank, scenario_manager)
            rwa += exposure_rwa
            if verbose:
                print(f"RWA for {exposure_name}: {exposure_rwa}")

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
        instruments = (i for i in bank.banking_book_assets() if ExposureChecker.is_sovereign_exposure(i, bank))
        return self._compute_rwa(RiskWeightTableForSovereignExposures, instruments)

    def _compute_PSE_exposures(self, bank: Bank, scenario_manager: ScenarioManager) -> float:
        """Compute the RWA for PSE exposures.

        TODO: An alternative to use the external ratings of sovereign, see CRE20.11.
        """
        instruments = (i for i in bank.banking_book_assets() if ExposureChecker.is_PSE_exposure(i, bank))
        return self._compute_rwa(RiskWeightTableForPSEBasedOnExternalRatingOfPSE, instruments)

    def _compute_MDB_exposures(self, bank: Bank, scenario_manager: ScenarioManager) -> float:
        """Compute the RWA for MDB exposures."""
        instruments = (i for i in bank.banking_book_assets() if ExposureChecker.is_MDB_exposure(i, bank))
        return self._compute_rwa(RiskWeightTableForMDBExposures, instruments)

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
        _filter = instrument_filter or ExposureChecker.is_bank_exposure

        total_rwa = 0.0
        for instrument in bank.banking_book_assets():
            issuer = instrument.issuer
            if not _filter(instrument, bank):
                continue
            if issuer.credit_rating > CreditRating.UNRATED:
                # Apply ECRA
                if ExposureChecker.is_short_term_exposure(instrument, bank):
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
        instruments = (i for i in bank.banking_book_assets() if ExposureChecker.is_covered_bond_exposure(i, bank))
        return self._compute_rwa(RiskWeightTableForRatedCoveredBondExposures, instruments)

    def _compute_securities_firms_exposures(self, bank: Bank, scenario_manager: ScenarioManager) -> float:
        """Compute the RWA for securities firms and other financial institutions exposures.

        Exposures to securities firms and other financial institutions will be treated as exposures to banks
        provided that these firms are subject to prudential standards and a level of supervision equivalent to
        those applied to banks (including capital and liquidity requirements).

        Exposures to all other securities firms and financial institutions will be treated as exposures to corporates.
        """
        return self._compute_bank_exposures(bank, scenario_manager, ExposureChecker.is_securities_firm_exposure)

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
        instruments = (i for i in bank.banking_book_assets() if ExposureChecker.is_corporate_exposure(i, bank))
        return self._compute_rwa(RiskWeightTableForCorporateExposures, instruments)

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
            if ExposureChecker.is_retail_exposure(instrument, bank):
                total_rwa += instrument.value * _get_risk_weight(instrument)
        return total_rwa

    def _compute_real_estate_exposures(self, bank: Bank, scenario_manager: ScenarioManager) -> float:
        """Compute the RWA for real estate exposures.

        The real estate exposure asset class consists of:
        1. Exposures secured by real estate that are classified as "regulatory real estate" exposures.
        2. Exposures secured by real estate that are classified as "other real estate" exposures.
        3. Exposures that are classified as "land acquisition, development and construction" (ADC) exposures.
        """

        def is_regulatory_residential(instrument: Instrument) -> bool:
            """TODO: Check if the exposure qualifies regulatory residential."""
            return False

        def is_regulatory_commercial(instrument: Instrument) -> bool:
            """TODO: Check if the exposure qualifies regulatory commercial."""
            return False

        def is_dependent_on_cash_flows_of_property(instrument: Instrument) -> bool:
            """TODO: Check if dependent on cash flows from the property."""
            return False

        def is_land_adc_exposure(instrument: Instrument) -> bool:
            """TODO: Check if the exposure qualifies land acquisition, development and construction exposures."""
            return False

        total_rwa = 0.0
        for instrument in bank.banking_book_assets():
            if not ExposureChecker.is_real_estate_exposure(instrument, bank):
                continue
            if is_regulatory_residential(instrument):
                if not is_dependent_on_cash_flows_of_property(instrument):
                    weight = RiskWeightTableForResidentialRealEstateNotDependentOnCashFlows.get_risk_weight(instrument)
                else:
                    weight = RiskWeightTableForResidentialRealEstateDependentOnCashFlows.get_risk_weight(instrument)
            elif is_regulatory_commercial(instrument):
                if not is_dependent_on_cash_flows_of_property(instrument):
                    weight = RiskWeightTableForCommercialRealEstateNotDependentOnCashFlows.get_risk_weight(instrument)
                else:
                    weight = RiskWeightTableForCommercialRealEstateDependentOnCashFlows.get_risk_weight(instrument)
            elif is_land_adc_exposure(instrument):
                weight = RiskWeightTableForLandADCExposure.get_risk_weight(instrument)
            else:
                weight = RiskWeightTableForOtherRealEstate.get_risk_weight(instrument)

            total_rwa += instrument.value * weight
        return total_rwa

    def _compute_currency_mismatch_exposures(self, bank: Bank, scenario_manager: ScenarioManager) -> float:
        """Compute the RWA for risk weight multiplier to certain exposures with currency mismatch."""
        raise NotImplementedError

    def _compute_off_balance_sheet_items(self, bank: Bank, scenario_manager: ScenarioManager) -> float:
        """Compute the RWA for off-balance sheet items."""
        raise NotImplementedError

    def _compute_counterparty_credit_risk_exposures(self, bank: Bank, scenario_manager: ScenarioManager) -> float:
        """Compute the RWA for exposures that give rise to counterparty credit risk.

        This is done in `brms.metrics.credit_risk.rwa.CreditRWACounterpartyCreditRisk` under the rules set out in CRE50 to CRE54.
        """
        return 0.0

    def _compute_credit_derivatives_exposures(self, bank: Bank, scenario_manager: ScenarioManager) -> float:
        """Compute the RWA for credit derivatives."""
        raise NotImplementedError

    def _compute_defaulted_exposures(self, bank: Bank, scenario_manager: ScenarioManager) -> float:
        """Compute the RWA for defaulted exposures."""
        raise NotImplementedError

    def _compute_other_assets_exposures(self, bank: Bank, scenario_manager: ScenarioManager) -> float:
        """Compute the RWA for other assets."""
        total_rwa = 0.0
        for instrument in bank.banking_book_assets():
            weight = 1.0
            if ExposureChecker.is_other_exposure(instrument, bank):
                if ExposureChecker.is_cash_exposure(instrument, bank):
                    weight = 0.0
                elif False:  # TODO: A 20% risk weight will apply to cash items in the process of collection.
                    weight = 0.2
                total_rwa += instrument.value * weight
        return total_rwa


class RiskWeightTable(ABC):
    """Base class for risk weight tables."""

    @classmethod
    @abstractmethod
    def get_risk_weight(cls, instrument: Instrument) -> float:
        """Get the risk."""


class RiskWeightTableByCreditRating(RiskWeightTable):
    """Base class for risk weight tables by credit rating."""

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


class RiskWeightTableForSovereignExposures(RiskWeightTableByCreditRating):
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


class RiskWeightTableForPSEBasedOnExternalRatingOfSovereign(RiskWeightTableByCreditRating):
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


class RiskWeightTableForPSEBasedOnExternalRatingOfPSE(RiskWeightTableByCreditRating):
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


class RiskWeightTableForMDBExposures(RiskWeightTableByCreditRating):
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


class RiskWeightTableForExposuresToBanks(RiskWeightTableByCreditRating):
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


class RiskWeightTableForShortTermExposuresToBanks(RiskWeightTableByCreditRating):
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


class RiskWeightTableForRatedCoveredBondExposures(RiskWeightTableByCreditRating):
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


class RiskWeightTableForCorporateExposures(RiskWeightTableByCreditRating):
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


class RiskWeightTableByLTV(RiskWeightTable):
    """Base class for risk weight tables by LTV."""


class RiskWeightTableForResidentialRealEstateNotDependentOnCashFlows(RiskWeightTableByLTV):
    """Class to represent the risk weight table for regulatory residential real estate exposures.

    Specifically those not dependent on cash flows generated by the property.

    This is Table 11 of CRE20.82.
    """

    @classmethod
    def get_risk_weight(cls, instrument: Instrument) -> float:
        """Get the risk weight based on the instrument's LTV ratio."""
        if not hasattr(instrument, "ltv"):
            error_message = "Instrument does not have an 'ltv' attribute"
            raise AttributeError(error_message)
        if 0 < instrument.ltv <= 0.5:
            return 0.2
        if instrument.ltv <= 0.6:
            return 0.25
        if instrument.ltv <= 0.8:
            return 0.3
        if instrument.ltv <= 0.9:
            return 0.4
        if instrument.ltv <= 1.0:
            return 0.5
        return 0.7


class RiskWeightTableForResidentialRealEstateDependentOnCashFlows(RiskWeightTableByLTV):
    """Class to represent the risk weight table for regulatory residential real estate exposures.

    Specifically those materially dependent on cash flows generated by the property.
    (e.g., Investment property)

    This is Table 12 of CRE20.84.
    """

    @classmethod
    def get_risk_weight(cls, instrument: Instrument) -> float:
        """Get the risk weight based on the instrument's LTV ratio."""
        if not hasattr(instrument, "ltv"):
            error_message = "Instrument does not have an 'ltv' attribute"
            raise AttributeError(error_message)
        if 0 < instrument.ltv <= 0.5:
            return 0.3
        if instrument.ltv <= 0.6:
            return 0.35
        if instrument.ltv <= 0.8:
            return 0.45
        if instrument.ltv <= 0.9:
            return 0.6
        if instrument.ltv <= 1.0:
            return 0.75
        return 1.05


class RiskWeightTableForCommercialRealEstateNotDependentOnCashFlows(RiskWeightTableByLTV):
    """Class to represent the risk weight table for regulatory commercial real estate exposures.

    Specifically those not dependent on cash flows generated by the property.

    This is Table 13 of CRE20.85.
    """

    @classmethod
    def get_risk_weight(cls, instrument: Instrument) -> float:
        """Get the risk weight based on the instrument's LTV ratio."""
        if not hasattr(instrument, "ltv"):
            error_message = "Instrument does not have an 'ltv' attribute"
            raise AttributeError(error_message)

        risk_weight_of_counterparty = RiskWeightTableForOtherRealEstate.get_risk_weight(instrument)

        if 0 < instrument.ltv <= 0.6:
            return min(0.6, risk_weight_of_counterparty)
        return risk_weight_of_counterparty


class RiskWeightTableForCommercialRealEstateDependentOnCashFlows(RiskWeightTableByLTV):
    """Class to represent the risk weight table for regulatory commercial real estate exposures.

    Specifically those are materially dependent on cash flows generated by the property.

    This is Table 14 of CRE20.87.
    """

    @classmethod
    def get_risk_weight(cls, instrument: Instrument) -> float:
        """Get the risk weight based on the instrument's LTV ratio."""
        if not hasattr(instrument, "ltv"):
            error_message = "Instrument does not have an 'ltv' attribute"
            raise AttributeError(error_message)
        if 0 < instrument.ltv <= 0.6:
            return 0.7
        if instrument.ltv <= 0.8:
            return 0.9
        return 1.1


class RiskWeightTableForOtherRealEstate(RiskWeightTable):
    """Class to represent the risk weight table for other real estate exposures.

    This is defined in CRE20.89.
    """

    @classmethod
    def get_risk_weight(cls, instrument: Instrument) -> float:
        """Get the risk weight based on the instrument's issuer and if it's dependent on cash flows."""
        # if is_dependent_on_cash_flows_of_property(instrument):
        if True:  # FIXME: assume cash flow dependent
            if instrument.issuer.is_individual():
                risk_weight_of_counterparty = 0.75
            elif instrument.issuer.is_SME():
                risk_weight_of_counterparty = 0.85
            else:
                # should be the risk weight for an unsecured exposure to this counterparty
                risk_weight_of_counterparty = 1.0
        else:
            risk_weight_of_counterparty = 1.5
        return risk_weight_of_counterparty


class RiskWeightTableForLandADCExposure(RiskWeightTable):
    """Class to represent the risk weight table for land ADC exposures.

    This is defined in CRE20.90 to CRE20.91.
    """

    @classmethod
    def get_risk_weight(cls, instrument: Instrument) -> float:
        """Get the risk weight.

        Land ADC exposures will be risk-weighted at 150%.

        If criteria in CRE20.91 are met, risk weight is 100%.
        For example, all developments have been pre-sold.

        To be conservative, let's use 150% here.
        """
        return 1.5
