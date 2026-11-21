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
        core_share: float = 0.0,
        core_maturity: float = 0.0,
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
            core_share: Share of the balance that is stable ("core") for interest-rate risk
                (Basel SRP31): in EVE it runs off over time instead of repricing overnight.
            core_maturity: Average life of the core balance in years; it runs off in equal monthly
                amounts over twice this period.

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
        if not 0 <= core_share <= 1:
            msg = f"core_share must be in [0, 1], got {core_share}"
            raise ValueError(msg)
        if core_maturity < 0 or (core_share > 0 and core_maturity <= 0):
            msg = f"core_maturity must be positive years when core_share is set, got {core_maturity}"
            raise ValueError(msg)
        self.core_share = float(core_share)
        self.core_maturity = float(core_maturity)

    def balance_factor(self, acquired: datetime.date, date: datetime.date) -> float:
        """Return the share of the acquired balance still deposited at close of business on *date*."""
        years = max(0, (date - acquired).days) / 365
        factor = math.exp(-self.runoff_rate * years)
        for day, fraction in self.withdrawals:
            if acquired < day <= date:
                factor *= 1 - fraction
        return factor

    def core_cash_flows(self, balance: float, date: datetime.date) -> list[tuple[datetime.date, float]]:
        """Return the core balance's principal run-off after *date*.

        Equal monthly amounts over twice the average life, so the average life is ``core_maturity``.
        Empty without a core share.
        """
        core = balance * self.core_share
        if core <= 0:
            return []
        months = max(1, round(24 * self.core_maturity))
        from dateutil.relativedelta import relativedelta

        return [(date + relativedelta(months=k), core / months) for k in range(1, months + 1)]

    def accept(self, visitor: Visitor) -> None:
        """Accept a visitor."""
        visitor.visit_deposit(self)  # type: ignore[union-attr]
