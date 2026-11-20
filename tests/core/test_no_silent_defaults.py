"""Missing inputs raise instead of being replaced by a default."""
# ruff: noqa: D103

from __future__ import annotations

import datetime
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from brms.core.enums import InterestSide, MeasurementBasis, PositionSide, TransactionType, TxMeta
from brms.core.exceptions import UnsupportedPositionError, ValuationError
from brms.core.models.accounting.bank_accounts import BankChartOfAccounts
from brms.core.models.accounting.journal import Journal
from brms.core.models.accounting.ledger import Ledger
from brms.core.models.instruments.base import CreditRating
from brms.core.models.instruments.bonds import CoveredBond
from brms.core.models.instruments.deposits import Deposit
from brms.core.models.transaction import Transaction
from brms.core.rules.context import RuleContext
from brms.core.rules.interest_accrual import InterestIncomeAccrualRule
from brms.core.services.accounting_service import AccountingService
from tests.support.engine import flat_yields, make_position, run_bank

_DAY = datetime.date(2024, 2, 1)


def _ctx() -> RuleContext:
    return RuleContext(date=_DAY, previous_date=_DAY - datetime.timedelta(days=1), market_state=None,
                       valuation_store=MagicMock())


def _deposit_position() -> object:
    return make_position(
        id="pos-dep", instrument_id="dep", basis=MeasurementBasis.NA, acquired=datetime.date(2024, 1, 1),
        cost=Decimal(1000), side=PositionSide.SHORT,
    )


def test_deposit_without_rate_raises() -> None:
    deposit = Deposit()
    deposit.id = "dep"
    yields = flat_yields(datetime.date(2021, 1, 4), datetime.date(2021, 1, 31))
    pos = make_position(id="pos-dep", instrument_id="dep", basis=MeasurementBasis.NA,
                        acquired=datetime.date(2021, 1, 4), cost=Decimal(1000), side=PositionSide.SHORT)
    with pytest.raises(UnsupportedPositionError, match="pos-dep"):
        run_bank([deposit], [pos], yields=yields, until=datetime.date(2021, 1, 8), checks=frozenset())


def test_interest_accrual_without_quantlib_instrument_raises() -> None:
    pos = make_position(
        id="pos-x", instrument_id="x", basis=MeasurementBasis.AMORTIZED_COST, acquired=datetime.date(2024, 1, 1),
        cost=Decimal(1000),
    )
    with pytest.raises(UnsupportedPositionError, match="pos-x"):
        InterestIncomeAccrualRule().generate(CoveredBond(name="x"), pos, _ctx())


def _ledger() -> Ledger:
    return Ledger(chart_of_accounts=BankChartOfAccounts(), journal=Journal())


def _settlement(accrued: str | None) -> Transaction:
    meta: tuple = ((TxMeta.SIDE, InterestSide.INCOME),)
    if accrued is not None:
        meta = (*meta, (TxMeta.ACCRUED_PORTION, accrued))
    return Transaction(
        id="s", type=TransactionType.INTEREST_SETTLEMENT, date=_DAY, amount=Decimal("100.00"), metadata=meta,
    )


def test_income_settlement_without_accrued_portion_raises() -> None:
    with pytest.raises(ValueError, match="accrued"):
        AccountingService().post(_settlement(None), _ledger())


def test_sub_cent_catch_up_clears_exactly_the_accrued_portion() -> None:
    ledger = _ledger()
    AccountingService().post(_settlement("100.004"), ledger)
    receivable = next(a for a in ledger.chart_of_accounts.all_accounts() if a.name == "Accrued Interest Receivable")
    assert receivable.balance() == pytest.approx(-100.004, abs=1e-9)  # noqa: S101


def test_position_without_quantlib_instrument_is_not_silently_unvalued() -> None:
    bond = CoveredBond(name="covered")
    bond.id = "CB"
    bond.credit_rating = CreditRating.AAA  # classifiable, so the run reaches valuation
    pos = make_position(
        id="pos-CB", instrument_id="CB", basis=MeasurementBasis.FVTPL, acquired=datetime.date(2021, 1, 4),
        cost=Decimal(1000),
    )
    yields = flat_yields(datetime.date(2021, 1, 4), datetime.date(2021, 1, 31))
    with pytest.raises(ValuationError, match="pos-CB"):
        run_bank([bond], [pos], yields=yields, until=datetime.date(2021, 1, 8), checks=frozenset())
