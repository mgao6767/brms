"""Operating inputs: the parts of profit that are not interest, marks or sales."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class OperatingConfig:
    """Bank-level operating flows, booked every calendar day.

    Attributes:
        noninterest_expense: Salaries, premises, technology and other costs per year (currency
            units of the bank's figures), paid in cash at 1/365 a day.
        noninterest_income: Fees, service charges and other non-interest income per year,
            received in cash at 1/365 a day.
        tax_rate: Income tax as a share of pre-tax profit. Tax is accrued so that the period's tax
            equals the rate times the period's pre-tax profit, floored at zero: losses after
            profits reverse tax already booked, and no deferred tax asset is recognised for losses.
        dividend_payout: Share of the period's profit after tax paid out as dividends. Dividends
            paid to date track payout x profit to date, floored at what has been paid: a later
            loss does not claw dividends back.

    """

    noninterest_expense: Decimal = Decimal(0)
    noninterest_income: Decimal = Decimal(0)
    tax_rate: float = 0.0
    dividend_payout: float = 0.0

    def __post_init__(self) -> None:
        """Validate the inputs."""
        if not 0 <= self.tax_rate < 1:
            msg = f"tax_rate must be a fraction in [0, 1), got {self.tax_rate} (give 0.21 for 21%)"
            raise ValueError(msg)
        if not 0 <= self.dividend_payout <= 1:
            msg = f"dividend_payout must be a fraction in [0, 1], got {self.dividend_payout} (give 0.3 for 30%)"
            raise ValueError(msg)
        if self.noninterest_expense < 0 or self.noninterest_income < 0:
            msg = "noninterest_expense and noninterest_income must be zero or positive"
            raise ValueError(msg)

    @property
    def is_zero(self) -> bool:
        """True when no operating flow is booked."""
        return (self.noninterest_expense == 0 and self.noninterest_income == 0 and self.tax_rate == 0
                and self.dividend_payout == 0)

    def to_json(self) -> dict[str, Any]:
        """Return the JSON form written to ``config.json``."""
        return {
            "noninterest_expense": str(self.noninterest_expense),
            "noninterest_income": str(self.noninterest_income),
            "tax_rate": self.tax_rate,
            "dividend_payout": self.dividend_payout,
        }

    @classmethod
    def from_json(cls, data: dict[str, Any] | None) -> OperatingConfig:
        """Build from the JSON form; missing keys take their defaults."""
        data = data or {}
        unknown = set(data) - {"noninterest_expense", "noninterest_income", "tax_rate", "dividend_payout"}
        if unknown:
            msg = f"Unknown operating fields: {sorted(unknown)}"
            raise ValueError(msg)
        return cls(
            noninterest_expense=Decimal(str(data.get("noninterest_expense", 0))),
            noninterest_income=Decimal(str(data.get("noninterest_income", 0))),
            tax_rate=float(data.get("tax_rate", 0.0)),
            dividend_payout=float(data.get("dividend_payout", 0.0)),
        )
