"""Tests for deposit instruments in the core domain model."""

# ruff: noqa: S101, ANN201, ANN204, ANN202, ANN001, PLR2004, ARG002

from brms.core.models.instruments.deposits import Cash, Deposit


def test_cash_instantiation() -> None:
    """Test that Cash can be instantiated with default value."""
    cash = Cash()
    assert cash is not None
    assert cash.name == "Cash"
    assert cash.value == 0.0


def test_cash_instantiation_with_value() -> None:
    """Test that Cash can be instantiated with a specific value."""
    cash = Cash(value=500.0)
    assert cash.value == 500.0


def test_cash_accept() -> None:
    """Test that Cash accept calls visitor.visit_cash."""

    class MockVisitor:
        def __init__(self) -> None:
            self.visited = False

        def visit_cash(self, instrument: Cash) -> None:
            self.visited = True

    cash = Cash(value=100.0)
    visitor = MockVisitor()
    cash.accept(visitor)
    assert visitor.visited


def test_deposit_instantiation() -> None:
    """Test that Deposit can be instantiated with default values."""
    deposit = Deposit()
    assert deposit is not None
    assert deposit.name == "Deposit"
    assert deposit.value == 0.0


def test_deposit_instantiation_with_params() -> None:
    """Test that Deposit can be instantiated with custom parameters."""
    deposit = Deposit(name="Savings Account", value=1000.0)
    assert deposit.name == "Savings Account"
    assert deposit.value == 1000.0


def test_deposit_accept() -> None:
    """Test that Deposit accept calls visitor.visit_deposit."""

    class MockVisitor:
        def __init__(self) -> None:
            self.visited = False

        def visit_deposit(self, instrument: Deposit) -> None:
            self.visited = True

    deposit = Deposit(value=200.0)
    visitor = MockVisitor()
    deposit.accept(visitor)
    assert visitor.visited
