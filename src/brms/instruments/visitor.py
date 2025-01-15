"""Defines the Visitor abstract base class for instrument visitors."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from brms.instruments.amortizing_fixed_rate_loan import AmortizingFixedRateLoan
    from brms.instruments.cash import Cash
    from brms.instruments.common_equity import CommonEquity
    from brms.instruments.covered_bond import CoveredBond
    from brms.instruments.credit_card import CreditCard
    from brms.instruments.fixed_rate_bond import FixedRateBond
    from brms.instruments.personal_loan import PersonalLoan


class Visitor(ABC):
    """Abstract base class for instrument visitors."""

    @abstractmethod
    def visit_cash(self, instrument: "Cash") -> Any:
        """Visit cash."""
        return instrument.value

    @abstractmethod
    def visit_common_equity(self, instrument: "CommonEquity") -> Any:
        """Visit common equity."""
        return instrument.value

    @abstractmethod
    def visit_fixed_rate_bond(self, instrument: "FixedRateBond") -> Any:
        """Visit a fixed rate bond."""

    @abstractmethod
    def visit_amortizing_fixed_rate_loan(self, instrument: "AmortizingFixedRateLoan") -> Any:
        """Visit an amortizing fixed rate bond."""

    @abstractmethod
    def visit_covered_bond(self, instrument: "CoveredBond") -> Any:
        """Visit a covered bond."""

    @abstractmethod
    def visit_personal_loan(self, instrument: "PersonalLoan") -> Any:
        """Visit a personal loan."""

    @abstractmethod
    def visit_credit_card(self, instrument: "CreditCard") -> Any:
        """Visit a credit card."""
