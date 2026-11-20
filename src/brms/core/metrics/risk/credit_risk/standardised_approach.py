"""Risk-weight tables of the Basel standardised approach for credit risk (CRE20).

The tables are used by :mod:`brms.core.metrics.risk.credit_risk.exposures`, which classifies
positions and applies them.
"""

from abc import ABC, abstractmethod
from typing import ClassVar

from brms.core.models.instruments.base import CreditRating, Instrument


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
        (CreditRating.BB_PLUS, CreditRating.BB_MINUS): 1.0,  # Table 10: BB+ to BB- 100%
        (CreditRating.B_PLUS, CreditRating.D): 1.5,  # below BB- 150%
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
            elif instrument.issuer.is_sme():
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
