"""Instrument base classes, enums, and registry for the core domain model."""

from brms.core.models.instruments.base import (
    BalanceSheetCategory,
    BookType,
    CompositeInstrument,
    CreditRating,
    Instrument,
    Issuer,
    IssuerType,
    MeasurementBasis,
)
from brms.core.models.instruments.registry import InstrumentRegistry

__all__ = [
    "BalanceSheetCategory",
    "BookType",
    "CompositeInstrument",
    "CreditRating",
    "Instrument",
    "InstrumentRegistry",
    "Issuer",
    "IssuerType",
    "MeasurementBasis",
    "default_instrument_registry",
]


def default_instrument_registry() -> InstrumentRegistry:
    """Return an InstrumentRegistry populated with all known instrument types."""
    from brms.core.models.instruments.bonds import CoveredBond, FixedRateBond, TreasuryBond, TreasuryNote
    from brms.core.models.instruments.deposits import Cash, Deposit
    from brms.core.models.instruments.equity import CommonEquity
    from brms.core.models.instruments.loans import (
        AmortizingFixedRateLoan,
        CommercialMortgage,
        CreditCard,
        Mortgage,
        PersonalLoan,
        ResidentialMortgage,
        VariableRateLoan,
    )
    from brms.core.models.instruments.other import (
        Commitment,
        LetterOfCredit,
        RepurchaseAgreement,
        StandByLetterOfCredit,
        TradeLetterOfCredit,
    )
    from brms.core.models.instruments.registry import CorporateInstrumentRegistry, LoanInstrumentRegistry

    LoanInstrumentRegistry.register(VariableRateLoan)
    CorporateInstrumentRegistry.register(VariableRateLoan)

    registry = InstrumentRegistry()
    for type_id, cls in [
        ("cash", Cash),
        ("deposit", Deposit),
        ("common_equity", CommonEquity),
        ("fixed_rate_bond", FixedRateBond),
        ("treasury_note", TreasuryNote),
        ("treasury_bond", TreasuryBond),
        ("covered_bond", CoveredBond),
        ("amortizing_fixed_rate_loan", AmortizingFixedRateLoan),
        ("mortgage", Mortgage),
        ("residential_mortgage", ResidentialMortgage),
        ("commercial_mortgage", CommercialMortgage),
        ("personal_loan", PersonalLoan),
        ("credit_card", CreditCard),
        ("commitment", Commitment),
        ("letter_of_credit", LetterOfCredit),
        ("standby_letter_of_credit", StandByLetterOfCredit),
        ("trade_letter_of_credit", TradeLetterOfCredit),
        ("repurchase_agreement", RepurchaseAgreement),
    ]:
        registry.register(type_id, cls)
    return registry
