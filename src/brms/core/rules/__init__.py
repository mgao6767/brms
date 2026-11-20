"""Accounting rules: protocol, registry, and concrete rule implementations."""

from brms.core.rules.amortization import AmortizationRule
from brms.core.rules.coupon import CouponPaymentRule
from brms.core.rules.deposit_interest import DepositFlowRule, DepositInterestAccrualRule, DepositInterestSettlementRule
from brms.core.rules.effective_interest import EffectiveInterestRule
from brms.core.rules.interest_accrual import InterestIncomeAccrualRule
from brms.core.rules.loan_interest_settlement import LoanInterestSettlementRule
from brms.core.rules.mark_to_market import MarkToMarketRule
from brms.core.rules.maturity import MaturityRule
from brms.core.rules.sale import SaleRule


def default_rules() -> dict[type, object]:
    """Return a class-keyed dict of all default accounting rule instances.

    The RuleEngine uses this dict to look up rule instances by class.
    Instruments declare which rule classes apply to them via
    ``applicable_rules``.
    """
    return {
        MaturityRule: MaturityRule(),
        SaleRule: SaleRule(),
        CouponPaymentRule: CouponPaymentRule(),
        MarkToMarketRule: MarkToMarketRule(),
        AmortizationRule: AmortizationRule(),
        DepositInterestAccrualRule: DepositInterestAccrualRule(),
        DepositInterestSettlementRule: DepositInterestSettlementRule(),
        DepositFlowRule: DepositFlowRule(),
        InterestIncomeAccrualRule: InterestIncomeAccrualRule(),
        EffectiveInterestRule: EffectiveInterestRule(),
        LoanInterestSettlementRule: LoanInterestSettlementRule(),
    }
