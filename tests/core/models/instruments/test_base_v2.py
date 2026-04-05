"""Tests for V2 Instrument base: no .value, ql_instrument, InstrumentType."""

# ruff: noqa: S101, ANN201, ANN001

import QuantLib as ql  # noqa: N813

from brms.core.enums import InstrumentType
from brms.core.models.instruments.base import Instrument
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
)
from brms.core.models.instruments.other import Commitment, LetterOfCredit, RepurchaseAgreement


def _make_bond(**kwargs) -> FixedRateBond:
    defaults = {
        "face_value": 1000.0,
        "coupon_rate": 0.05,
        "issue_date": ql.Date(1, 1, 2020),
        "maturity_date": ql.Date(1, 1, 2025),
    }
    defaults.update(kwargs)
    return FixedRateBond(**defaults)


def _make_loan(**kwargs) -> AmortizingFixedRateLoan:
    defaults = {
        "face_value": 100_000.0,
        "interest_rate": 0.05,
        "issue_date": ql.Date(1, 1, 2020),
        "maturity": ql.Period(5, ql.Years),
    }
    defaults.update(kwargs)
    return AmortizingFixedRateLoan(**defaults)


# --- No _value attribute ---


def test_instrument_has_no_value_attribute() -> None:
    """Instrument instances should not have a _value attribute."""
    bond = _make_bond()
    assert not hasattr(bond, "_value")


def test_instrument_has_no_value_property() -> None:
    """Instrument instances should not expose a .value property."""
    bond = _make_bond()
    # value should not be a property on the class
    assert not isinstance(Instrument.__dict__.get("value"), property)


# --- ql_instrument defaults to None ---


def test_ql_instrument_defaults_to_none_for_cash() -> None:
    """Non-QL instruments default ql_instrument to None."""
    cash = Cash()
    assert cash.ql_instrument is None


def test_ql_instrument_defaults_to_none_for_deposit() -> None:
    """Deposit has ql_instrument = None."""
    deposit = Deposit()
    assert deposit.ql_instrument is None


def test_ql_instrument_defaults_to_none_for_equity() -> None:
    """CommonEquity has ql_instrument = None."""
    eq = CommonEquity()
    assert eq.ql_instrument is None


def test_ql_instrument_set_for_bond() -> None:
    """FixedRateBond should have a ql_instrument set."""
    bond = _make_bond()
    assert bond.ql_instrument is not None


def test_ql_instrument_set_for_loan() -> None:
    """AmortizingFixedRateLoan should have a ql_instrument set."""
    loan = _make_loan()
    assert loan.ql_instrument is not None


# --- instrument_type correctness ---


def test_fixed_rate_bond_instrument_type() -> None:
    """FixedRateBond sets instrument_type to FIXED_RATE_BOND."""
    bond = _make_bond()
    assert bond.instrument_type == InstrumentType.FIXED_RATE_BOND


def test_treasury_note_instrument_type() -> None:
    """TreasuryNote sets instrument_type to TREASURY_NOTE."""
    note = TreasuryNote(
        face_value=1000.0,
        coupon_rate=0.03,
        issue_date=ql.Date(1, 1, 2020),
        maturity_date=ql.Date(1, 1, 2025),
    )
    assert note.instrument_type == InstrumentType.TREASURY_NOTE


def test_treasury_bond_instrument_type() -> None:
    """TreasuryBond sets instrument_type to TREASURY_BOND."""
    bond = TreasuryBond(
        face_value=1000.0,
        coupon_rate=0.04,
        issue_date=ql.Date(1, 1, 2020),
        maturity_date=ql.Date(1, 1, 2040),
    )
    assert bond.instrument_type == InstrumentType.TREASURY_BOND


def test_cash_instrument_type() -> None:
    """Cash sets instrument_type to CASH."""
    assert Cash().instrument_type == InstrumentType.CASH


def test_deposit_instrument_type() -> None:
    """Deposit sets instrument_type to DEPOSIT."""
    assert Deposit().instrument_type == InstrumentType.DEPOSIT


def test_common_equity_instrument_type() -> None:
    """CommonEquity sets instrument_type to COMMON_EQUITY."""
    assert CommonEquity().instrument_type == InstrumentType.COMMON_EQUITY


def test_amortizing_loan_instrument_type() -> None:
    """AmortizingFixedRateLoan sets instrument_type to AMORTIZING_FIXED_RATE_LOAN."""
    loan = _make_loan()
    assert loan.instrument_type == InstrumentType.AMORTIZING_FIXED_RATE_LOAN


def test_residential_mortgage_instrument_type() -> None:
    """ResidentialMortgage sets instrument_type to RESIDENTIAL_MORTGAGE."""
    m = ResidentialMortgage(
        face_value=200_000.0,
        interest_rate=0.04,
        issue_date=ql.Date(1, 1, 2020),
        maturity=ql.Period(30, ql.Years),
    )
    assert m.instrument_type == InstrumentType.RESIDENTIAL_MORTGAGE


def test_commercial_mortgage_instrument_type() -> None:
    """CommercialMortgage sets instrument_type to COMMERCIAL_MORTGAGE."""
    m = CommercialMortgage(
        face_value=500_000.0,
        interest_rate=0.05,
        issue_date=ql.Date(1, 1, 2020),
        maturity=ql.Period(10, ql.Years),
    )
    assert m.instrument_type == InstrumentType.COMMERCIAL_MORTGAGE
