"""Deposit instrument classes for the core domain model."""

from __future__ import annotations

import datetime
import math
from typing import TYPE_CHECKING

from brms.core.enums import InstrumentType
from brms.core.models.instruments.base import Instrument
from brms.core.rules.deposit_interest import DepositFlowRule, DepositInterestAccrualRule, DepositInterestSettlementRule

if TYPE_CHECKING:
    from collections.abc import Sequence

    from brms.core.visitors.base import Visitor


class Cash(Instrument):
    """A class to represent cash."""

    def __init__(self) -> None:
        """Initialize cash."""
        super().__init__(name="Cash")
        self.instrument_type = InstrumentType.CASH

    def accept(self, visitor: Visitor) -> None:
        """Accept a visitor."""
        visitor.visit_cash(self)  # type: ignore[union-attr]


class Deposit(Instrument):
    """A class to represent customer deposit."""

    applicable_rules = frozenset({DepositInterestAccrualRule, DepositInterestSettlementRule, DepositFlowRule})

    def __init__(  # noqa: PLR0913
        self,
        *,
        name: str = "Deposit",
        interest_rate: float | None = None,
        beta: float = 0.0,
        runoff_rate: float = 0.0,
        withdrawals: Sequence[tuple[datetime.date | str, float]] = (),
        reference_tenor: str = "3 Mo",
    ) -> None:
        """Initialize a deposit.

        Args:
            name: The name of the deposit.
            interest_rate: Annual rate paid at acquisition (0.0 for a non-interest-bearing deposit).
            beta: Share of the change in the reference market rate since acquisition passed to
                depositors; the rate is floored at zero.
            runoff_rate: Continuous annual rate at which the balance leaves the bank.
            withdrawals: Scheduled outflows ``(date, fraction of the balance then outstanding)``.
            reference_tenor: Yield column the deposit rate follows (default 3-month Treasury).

        """
        super().__init__(name=name)
        self.instrument_type = InstrumentType.DEPOSIT
        self.interest_rate = interest_rate
        self.beta = float(beta)
        self.runoff_rate = float(runoff_rate)
        self.withdrawals = tuple(
            (datetime.date.fromisoformat(d) if isinstance(d, str) else d, float(f)) for d, f in withdrawals
        )
        self.reference_tenor = reference_tenor

    def balance_factor(self, acquired: datetime.date, date: datetime.date) -> float:
        """Return the share of the acquired balance still deposited at close of business on *date*."""
        years = max(0, (date - acquired).days) / 365
        factor = math.exp(-self.runoff_rate * years)
        for day, fraction in self.withdrawals:
            if acquired < day <= date:
                factor *= 1 - fraction
        return factor

    def accept(self, visitor: Visitor) -> None:
        """Accept a visitor."""
        visitor.visit_deposit(self)  # type: ignore[union-attr]
