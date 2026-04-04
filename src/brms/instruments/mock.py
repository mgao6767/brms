"""Contains mock instruments and visitors for testing purposes."""

from typing import TYPE_CHECKING, Optional

from brms.instruments.base import Instrument
from brms.instruments.visitors.valuation import ValuationVisitor
from brms.models.scenario import ScenarioManager

if TYPE_CHECKING:
    from brms.instruments.amortizing_fixed_rate_loan import AmortizingFixedRateLoan
    from brms.instruments.base import CreditRating, Issuer
    from brms.instruments.covered_bond import CoveredBond
    from brms.instruments.credit_card import CreditCard
    from brms.instruments.fixed_rate_bond import FixedRateBond
    from brms.instruments.personal_loan import PersonalLoan
    from brms.instruments.visitors import Visitor
    from brms.models.base import BookType


class MockInstrument(Instrument):
    """A mock instrument for testing purposes."""

    def __init__(
        self,
        name: str,
        book_type: Optional["BookType"] = None,
        credit_rating: Optional["CreditRating"] = None,
        issuer: Optional["Issuer"] = None,
        parent: Optional["Instrument"] = None,
    ) -> None:
        """Initialize a composite instrument with an empty list of instruments."""
        super().__init__(name, book_type, credit_rating, issuer, parent)

    def accept(self, visitor: "Visitor") -> None:
        """Accept a visitor that processes this mock instrument."""
        visitor.visit_mock_instrument(self)


class MockValuationVisitor(ValuationVisitor):
    """A mock valuation visitor that sets a new value for mock instruments."""

    def __init__(self, new_value: float) -> None:
        """Initialize the MockValuationVisitor with a new value.

        :param new_value: The new value to set for the mock instrument.
        """
        sm = ScenarioManager()
        super().__init__(scenario_manager=sm, valuation_date=None)
        self.new_value = new_value

    def visit_mock_instrument(self, instrument: "MockInstrument") -> None:
        """Visit a mock instrument."""
        instrument.value = self.new_value

    def visit_fixed_rate_bond(self, instrument: "FixedRateBond") -> None:
        """Value a fixed rate bond."""

    def visit_amortizing_fixed_rate_loan(self, instrument: "AmortizingFixedRateLoan") -> None:
        """Value an amortizing fixed rate bond."""

    def visit_covered_bond(self, instrument: "CoveredBond") -> None:
        """Value a covered bond."""

    def visit_personal_loan(self, instrument: "PersonalLoan") -> None:
        """Value a personal loan."""

    def visit_credit_card(self, instrument: "CreditCard") -> None:
        """Value a credit card."""
