"""Defines the Visitor abstract base class for instrument visitors."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

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
    def visit_cash(self, instrument: "Cash") -> None:
        """Visit cash."""

    @abstractmethod
    def visit_common_equity(self, instrument: "CommonEquity") -> None:
        """Visit common equity."""

    @abstractmethod
    def visit_fixed_rate_bond(self, instrument: "FixedRateBond") -> None:
        """Visit a fixed rate bond."""

    @abstractmethod
    def visit_amortizing_fixed_rate_loan(self, instrument: "AmortizingFixedRateLoan") -> None:
        """Visit an amortizing fixed rate bond."""

    @abstractmethod
    def visit_covered_bond(self, instrument: "CoveredBond") -> None:
        """Visit a covered bond."""

    @abstractmethod
    def visit_personal_loan(self, instrument: "PersonalLoan") -> None:
        """Visit a personal loan."""

    @abstractmethod
    def visit_credit_card(self, instrument: "CreditCard") -> None:
        """Visit a credit card."""
