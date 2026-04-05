"""Tests for deposit instruments in the core domain model."""

# ruff: noqa: S101, ANN201, ANN204, ANN202, ANN001, PLR2004, ARG002

from brms.core.enums import InstrumentType
from brms.core.models.instruments.deposits import Cash, Deposit


def test_cash_instantiation() -> None:
    """Test that Cash can be instantiated with default values."""
    cash = Cash()
    assert cash is not None
    assert cash.name == "Cash"
    assert cash.instrument_type == InstrumentType.CASH


def test_cash_ql_instrument_is_none() -> None:
    """Cash has no QL instrument."""
    cash = Cash()
    assert cash.ql_instrument is None


def test_cash_accept() -> None:
    """Test that Cash accept calls visitor.visit_cash."""

    class MockVisitor:
        def __init__(self) -> None:
            self.visited = False

        def visit_cash(self, instrument: Cash) -> None:
            self.visited = True

    cash = Cash()
    visitor = MockVisitor()
    cash.accept(visitor)
    assert visitor.visited


def test_deposit_instantiation() -> None:
    """Test that Deposit can be instantiated with default values."""
    deposit = Deposit()
    assert deposit is not None
    assert deposit.name == "Deposit"
    assert deposit.instrument_type == InstrumentType.DEPOSIT


def test_deposit_instantiation_with_name() -> None:
    """Test that Deposit can be instantiated with a custom name."""
    deposit = Deposit(name="Savings Account")
    assert deposit.name == "Savings Account"


def test_deposit_accept() -> None:
    """Test that Deposit accept calls visitor.visit_deposit."""

    class MockVisitor:
        def __init__(self) -> None:
            self.visited = False

        def visit_deposit(self, instrument: Deposit) -> None:
            self.visited = True

    deposit = Deposit()
    visitor = MockVisitor()
    deposit.accept(visitor)
    assert visitor.visited
