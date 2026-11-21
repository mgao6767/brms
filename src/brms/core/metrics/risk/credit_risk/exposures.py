"""Credit RWA under the Basel standardised approach (CRE20), from per-position exposures.

Each open LONG bond or loan position is an exposure equal to its carrying value plus accrued
interest on the day. The position is classified by its issuer and instrument type and weighted
with the CRE20 tables in ``standardised_approach``. Balance-sheet assets that are not positions
(cash, property, interbank receivables) are weighted by account. An exposure that cannot be
classified raises ``UnsupportedPositionError``; nothing is weighted by default.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum, auto
from typing import TYPE_CHECKING

from brms.core.enums import InstrumentType, MeasurementBasis, PositionSide, ValuationType
from brms.core.exceptions import UnsupportedPositionError, ValuationError
from brms.core.metrics.risk.credit_risk.standardised_approach import (
    RiskWeightTableForCommercialRealEstateNotDependentOnCashFlows,
    RiskWeightTableForCorporateExposures,
    RiskWeightTableForExposuresToBanks,
    RiskWeightTableForMDBExposures,
    RiskWeightTableForPSEBasedOnExternalRatingOfPSE,
    RiskWeightTableForRatedCoveredBondExposures,
    RiskWeightTableForResidentialRealEstateNotDependentOnCashFlows,
    RiskWeightTableForSovereignExposures,
)
from brms.core.models.instruments.base import CreditRating, IssuerType

if TYPE_CHECKING:
    import datetime

    from brms.core.models.bank import Bank
    from brms.core.models.instruments.base import Instrument
    from brms.core.models.position import Position
    from brms.core.stores.valuation_store import ValuationStore


class ExposureClass(Enum):
    """Standardised-approach exposure classes the lab supports."""

    SOVEREIGN = auto()
    PSE = auto()
    MDB = auto()
    BANK = auto()
    COVERED_BOND = auto()
    RESIDENTIAL_REAL_ESTATE = auto()
    COMMERCIAL_REAL_ESTATE = auto()
    CORPORATE = auto()
    RETAIL = auto()
    CASH = auto()
    OTHER_ASSETS = auto()


@dataclass(frozen=True)
class RWALine:
    """One weighted exposure: a position (key = position id) or a balance-sheet account (key = name)."""

    key: str
    exposure_class: ExposureClass
    exposure: Decimal
    risk_weight: Decimal

    @property
    def rwa(self) -> Decimal:
        """Risk-weighted amount."""
        return self.exposure * self.risk_weight


@dataclass(frozen=True)
class CreditRWA:
    """Credit RWA with its line items."""

    items: tuple[RWALine, ...]

    @property
    def total(self) -> Decimal:
        """Total credit RWA."""
        return sum((item.rwa for item in self.items), Decimal(0))


_CORPORATE_ISSUERS = (
    IssuerType.CORPORATE,
    IssuerType.SME,
    IssuerType.SECURITIES_FIRM,
    IssuerType.FINANCIAL_INSTITUTION,
    IssuerType.INSURANCE_COMPANY,
)
_RESIDENTIAL = frozenset({InstrumentType.MORTGAGE, InstrumentType.RESIDENTIAL_MORTGAGE})
_RETAIL_WEIGHT = Decimal("0.75")  # regulatory retail, CRE20.65
_MAX_LTV = 2.0  # loan-to-value is a fraction; anything larger is almost certainly a percentage

# Balance-sheet asset accounts weighted directly. Accounts holding positions (investments, loans,
# FVTPL assets, accrued interest) are covered by the position lines; intangibles are deducted
# from CET1 instead of being weighted.
ACCOUNT_WEIGHTS: dict[str, tuple[ExposureClass, Decimal]] = {
    "Cash and Cash Equivalents": (ExposureClass.CASH, Decimal(0)),
    "Receivables from Financial Institutions": (ExposureClass.OTHER_ASSETS, Decimal(1)),
    "Property, Plant and Equipment": (ExposureClass.OTHER_ASSETS, Decimal(1)),
    "Other Assets": (ExposureClass.OTHER_ASSETS, Decimal(1)),
}


def _weight(value: float) -> Decimal:
    return Decimal(str(value))


def classify(instrument: Instrument, position: Position) -> tuple[ExposureClass, Decimal]:
    """Return the exposure class and risk weight of a position.

    Raises:
        UnsupportedPositionError: the position cannot be classified or weighted.

    """
    outcome = _classify(instrument)
    if isinstance(outcome, str):
        msg = f"Position {position.id} cannot be risk-weighted: {outcome}"
        raise UnsupportedPositionError(msg)
    return outcome


def _classify(instrument: Instrument) -> tuple[ExposureClass, Decimal] | str:  # noqa: C901, PLR0911
    """Return (class, weight), or the reason the instrument cannot be classified."""
    inst_type = getattr(instrument, "instrument_type", None)
    issuer = getattr(instrument, "issuer", None)
    if inst_type == InstrumentType.COVERED_BOND:
        if getattr(instrument, "credit_rating", CreditRating.UNRATED) == CreditRating.UNRATED:
            return "unrated covered bonds are not supported"
        table = RiskWeightTableForRatedCoveredBondExposures
        return ExposureClass.COVERED_BOND, _weight(table.get_risk_weight(instrument))
    if inst_type in _RESIDENTIAL or inst_type == InstrumentType.COMMERCIAL_MORTGAGE:
        return _classify_real_estate(instrument, inst_type, issuer)
    if issuer is None:
        return "the instrument has no issuer"
    kind = issuer.issuer_type
    # CRE21: an issue-specific rating takes precedence over the issuer's rating.
    issue_rated = getattr(instrument, "credit_rating", CreditRating.UNRATED) not in (None, CreditRating.UNRATED)
    by_issuer = not issue_rated
    rating = instrument.credit_rating if issue_rated else issuer.credit_rating
    if kind == IssuerType.SOVEREIGN:
        table = RiskWeightTableForSovereignExposures
        return ExposureClass.SOVEREIGN, _weight(table.get_risk_weight(instrument, use_issuer_rating=by_issuer))
    if kind == IssuerType.PSE:
        table = RiskWeightTableForPSEBasedOnExternalRatingOfPSE
        return ExposureClass.PSE, _weight(table.get_risk_weight(instrument, use_issuer_rating=by_issuer))
    if kind == IssuerType.MDB:
        table = RiskWeightTableForMDBExposures
        return ExposureClass.MDB, _weight(table.get_risk_weight(instrument, use_issuer_rating=by_issuer))
    if kind == IssuerType.BANK:
        if rating == CreditRating.UNRATED:
            return "unrated bank exposures need SCRA grades, which are not modelled"
        table = RiskWeightTableForExposuresToBanks
        return ExposureClass.BANK, _weight(table.get_risk_weight(instrument, use_issuer_rating=by_issuer))
    if kind in _CORPORATE_ISSUERS:
        table = RiskWeightTableForCorporateExposures
        return ExposureClass.CORPORATE, _weight(table.get_risk_weight(instrument, use_issuer_rating=by_issuer))
    if kind == IssuerType.INDIVIDUAL:
        return ExposureClass.RETAIL, _RETAIL_WEIGHT
    return f"issuer type {kind.name} is not supported"


def _classify_real_estate(
    instrument: Instrument, inst_type: InstrumentType, issuer: object,
) -> tuple[ExposureClass, Decimal] | str:
    ltv = getattr(instrument, "ltv", None)
    if ltv is None:
        return "the mortgage has no loan-to-value ratio (ltv)"
    if not 0 < ltv <= _MAX_LTV:
        return f"ltv {ltv} is not a fraction in (0, {_MAX_LTV}] (give 0.8 for 80%)"
    if inst_type == InstrumentType.COMMERCIAL_MORTGAGE:
        if issuer is None:
            return "the commercial mortgage has no issuer"
        table = RiskWeightTableForCommercialRealEstateNotDependentOnCashFlows
        return ExposureClass.COMMERCIAL_REAL_ESTATE, _weight(table.get_risk_weight(instrument))
    table = RiskWeightTableForResidentialRealEstateNotDependentOnCashFlows
    return ExposureClass.RESIDENTIAL_REAL_ESTATE, _weight(table.get_risk_weight(instrument))


def validate_exposures(bank: Bank) -> None:
    """Classify every open long valued position, raising for the first one that cannot be weighted."""
    for position in bank.positions.open_positions():
        if position.side == PositionSide.LONG and position.measurement_basis != MeasurementBasis.NA:
            classify(bank.instruments.get(position.instrument_id), position)


def credit_rwa(
    bank: Bank,
    valuation_store: ValuationStore,
    date: datetime.date,
    balance_sheet: dict | None = None,
) -> CreditRWA:
    """Compute credit RWA on *date* (after that day's valuation and posting).

    *balance_sheet* is the as-if-closed balance sheet of the day (computed if not given).
    """
    items: list[RWALine] = []
    for position in bank.positions.open_positions():
        if position.side != PositionSide.LONG:
            continue
        if position.measurement_basis == MeasurementBasis.NA:
            continue  # cash and similar holdings live in balance-sheet accounts, weighted below
        instrument = bank.instruments.get(position.instrument_id)
        carrying = valuation_store.get(position.id, date, ValuationType.CARRYING_VALUE)
        accrued = valuation_store.get(position.id, date, ValuationType.ACCRUED_INTEREST)
        if carrying is None or accrued is None:
            msg = f"Position {position.id} has no carrying value or accrued interest on {date}"
            raise ValuationError(msg)
        exposure_class, weight = classify(instrument, position)
        items.append(RWALine(position.id, exposure_class, Decimal(carrying) + Decimal(accrued), weight))

    if balance_sheet is None:
        from brms.core.services.reporting_service import ReportingService

        balance_sheet = ReportingService().balance_sheet(bank.ledger, date=date)
    balances = {row["account"]: row["balance"] for row in balance_sheet["assets"]}
    for account, (exposure_class, weight) in ACCOUNT_WEIGHTS.items():
        balance = Decimal(str(balances.get(account, 0.0)))
        if balance:
            items.append(RWALine(account, exposure_class, balance, weight))
    return CreditRWA(tuple(items))
