"""Defines the Visitor abstract base class for instrument visitors."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from brms.core.models.instruments.bonds import CoveredBond, FixedRateBond
    from brms.core.models.instruments.deposits import Cash, Deposit
    from brms.core.models.instruments.equity import CommonEquity
    from brms.core.models.instruments.loans import AmortizingFixedRateLoan, CreditCard, PersonalLoan


class Visitor(ABC):
    """Abstract base class for instrument visitors."""

    @abstractmethod
    def visit_cash(self, instrument: "Cash") -> None:
        """Visit cash."""

    @abstractmethod
    def visit_deposit(self, instrument: "Deposit") -> None:
        """Visit deposit."""

    @abstractmethod
    def visit_common_equity(self, instrument: "CommonEquity") -> None:
        """Visit common equity."""

    @abstractmethod
    def visit_fixed_rate_bond(self, instrument: "FixedRateBond") -> None:
        """Visit a fixed rate bond."""

    @abstractmethod
    def visit_amortizing_fixed_rate_loan(self, instrument: "AmortizingFixedRateLoan") -> None:
        """Visit an amortizing fixed rate loan."""

    @abstractmethod
    def visit_covered_bond(self, instrument: "CoveredBond") -> None:
        """Visit a covered bond."""

    @abstractmethod
    def visit_personal_loan(self, instrument: "PersonalLoan") -> None:
        """Visit a personal loan."""

    @abstractmethod
    def visit_credit_card(self, instrument: "CreditCard") -> None:
        """Visit a credit card."""
