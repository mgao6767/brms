"""Tests for bond instruments in the core domain model."""

# ruff: noqa: S101, ANN201, ANN204, ANN202, ANN001, PLR2004, ARG002

import datetime

import pytest
import QuantLib as ql  # noqa: N813

from brms.core.models.instruments.bonds import CoveredBond, FixedRateBond, TreasuryNote


@pytest.fixture
def fixed_rate_bond() -> FixedRateBond:
    """Fixture to create a FixedRateBond instance."""
    return FixedRateBond(
        face_value=1000.0,
        coupon_rate=0.05,
        issue_date=ql.Date(1, 1, 2020),
        maturity_date=ql.Date(1, 1, 2030),
    )


def test_fixed_rate_bond_instantiation(fixed_rate_bond: FixedRateBond) -> None:
    """Test that FixedRateBond can be instantiated with basic properties."""
    assert fixed_rate_bond is not None
    assert fixed_rate_bond.name == "5.00% 2030/1/1 Fixed Rate Bond"
    assert fixed_rate_bond.instrument is not None


def test_fixed_rate_bond_maturity_date(fixed_rate_bond: FixedRateBond) -> None:
    """Test the maturity date property."""
    assert fixed_rate_bond.maturity_date == datetime.date(2030, 1, 1)


def test_fixed_rate_bond_issue_date(fixed_rate_bond: FixedRateBond) -> None:
    """Test the issue date property."""
    assert fixed_rate_bond.issue_date == datetime.date(2020, 1, 1)


def test_fixed_rate_bond_notional(fixed_rate_bond: FixedRateBond) -> None:
    """Test notional value on a date before maturity."""
    notional = fixed_rate_bond.notional(datetime.date(2025, 1, 1))
    assert notional == 1000.0


def test_fixed_rate_bond_notional_at_maturity(fixed_rate_bond: FixedRateBond) -> None:
    """Test notional value at maturity date is zero."""
    notional = fixed_rate_bond.notional(datetime.date(2030, 1, 1))
    assert notional == 0.0


def test_fixed_rate_bond_payment_schedule(fixed_rate_bond: FixedRateBond) -> None:
    """Test that payment schedule returns a non-empty list."""
    schedule = fixed_rate_bond.payment_schedule()
    assert isinstance(schedule, list)
    assert len(schedule) > 0


def test_fixed_rate_bond_accept(fixed_rate_bond: FixedRateBond) -> None:
    """Test that accept calls visitor.visit_fixed_rate_bond."""

    class MockVisitor:
        def __init__(self) -> None:
            self.visited = False

        def visit_fixed_rate_bond(self, instrument: FixedRateBond) -> None:
            self.visited = True

    visitor = MockVisitor()
    fixed_rate_bond.accept(visitor)
    assert visitor.visited


@pytest.fixture
def treasury_note() -> TreasuryNote:
    """Fixture to create a TreasuryNote instance."""
    return TreasuryNote(
        face_value=1000.0,
        coupon_rate=0.04,
        issue_date=ql.Date(1, 6, 2022),
        maturity_date=ql.Date(1, 6, 2027),
    )


def test_treasury_note_instantiation(treasury_note: TreasuryNote) -> None:
    """Test that TreasuryNote can be instantiated."""
    assert treasury_note is not None
    assert "Treasury Note" in treasury_note.name
    assert "Treasury Note" in treasury_note.name


def test_treasury_note_maturity_date(treasury_note: TreasuryNote) -> None:
    """Test the maturity date property of TreasuryNote."""
    assert treasury_note.maturity_date == datetime.date(2027, 6, 1)


def test_treasury_note_notional(treasury_note: TreasuryNote) -> None:
    """Test notional value of TreasuryNote before maturity."""
    notional = treasury_note.notional(datetime.date(2025, 1, 1))
    assert notional == 1000.0


def test_covered_bond_instantiation() -> None:
    """Test that CoveredBond can be instantiated."""
    bond = CoveredBond(name="Covered Bond A")
    assert bond is not None
    assert bond.name == "Covered Bond A"


def test_covered_bond_accept() -> None:
    """Test that CoveredBond accept calls visitor.visit_covered_bond."""

    class MockVisitor:
        def __init__(self) -> None:
            self.visited = False

        def visit_covered_bond(self, instrument: CoveredBond) -> None:
            self.visited = True

    bond = CoveredBond(name="Test Bond")
    visitor = MockVisitor()
    bond.accept(visitor)
    assert visitor.visited
