"""Accounting rules: protocol, registry, and concrete rule implementations."""

from brms.core.rules.amortization import AmortizationRule
from brms.core.rules.coupon import CouponPaymentRule
from brms.core.rules.deposit_interest import DepositInterestAccrualRule, DepositInterestSettlementRule
from brms.core.rules.interest_accrual import InterestIncomeAccrualRule
from brms.core.rules.mark_to_market import MarkToMarketRule
from brms.core.rules.maturity import MaturityRule


def default_rules() -> tuple:
    """Return a tuple of all default accounting rule instances."""
    return (
        MaturityRule(),
        CouponPaymentRule(),
        MarkToMarketRule(),
        AmortizationRule(),
        DepositInterestAccrualRule(),
        DepositInterestSettlementRule(),
        InterestIncomeAccrualRule(),
    )
