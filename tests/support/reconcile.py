"""Reconciliation of ledger control accounts against per-position values.

Every account that holds positions must equal the sum of those positions'
values in the ValuationStore, every day. This is the check that catches an
accounting entry that does not match the economics of the position it books.
"""

from __future__ import annotations

from decimal import Decimal
from enum import Enum, auto
from typing import TYPE_CHECKING

from brms.core.enums import InstrumentType, MeasurementBasis, PositionSide, ValuationType
from brms.core.services.reporting_service import ReportingService

if TYPE_CHECKING:
    import datetime

    from brms.core.models.instruments.base import Instrument
    from brms.core.models.position import Position
    from brms.core.services.simulation_service import SimulationService

_CENT = Decimal("0.01")

LOAN_TYPES = frozenset({
    InstrumentType.RESIDENTIAL_MORTGAGE,
    InstrumentType.COMMERCIAL_MORTGAGE,
    InstrumentType.MORTGAGE,
    InstrumentType.AMORTIZING_FIXED_RATE_LOAN,
    InstrumentType.VARIABLE_RATE_LOAN,
})


class Check(Enum):
    """The reconciliation identities: the seven of the design (Part 8), plus deposits."""

    BALANCE = auto()
    AMORTIZED_COST_SECURITIES = auto()
    FVOCI_SECURITIES = auto()
    FVTPL_ASSETS = auto()
    LOANS = auto()
    ACCRUED_INTEREST = auto()
    AOCI = auto()
    DEPOSITS = auto()
    INTEREST_PAYABLE = auto()


def account_balance(sim: SimulationService, name: str) -> Decimal:
    """Return the balance of the named ledger account."""
    for account in sim.bank.ledger.chart_of_accounts.all_accounts():
        if account.name == name:
            return Decimal(str(account.balance()))
    msg = f"No account named {name!r}"
    raise KeyError(msg)


def _is_loan(instrument: Instrument) -> bool:
    return getattr(instrument, "instrument_type", None) in LOAN_TYPES


def _value(sim: SimulationService, position: Position, date: datetime.date, vtype: ValuationType) -> Decimal:
    value = sim.valuation_store.get(position.id, date, vtype)
    if value is None:
        msg = f"{position.id} has no {vtype.name} on {date}"
        raise AssertionError(msg)
    return Decimal(str(value))


def _compare(
    check: Check,
    date: datetime.date,
    account: str,
    balance: Decimal,
    parts: dict[str, Decimal],
) -> None:
    total = sum(parts.values(), Decimal(0))
    tolerance = _CENT * max(1, len(parts))
    if abs(balance - total) > tolerance:
        detail = ", ".join(f"{k}={v:.2f}" for k, v in sorted(parts.items())) or "no positions"
        msg = (
            f"{check.name} failed on {date}: {account} = {balance:.2f} but positions sum to {total:.2f} "
            f"(difference {balance - total:.2f}); {detail}"
        )
        raise AssertionError(msg)


def assert_books_reconcile(  # noqa: C901
    sim: SimulationService,
    date: datetime.date,
    checks: frozenset[Check] = frozenset(Check),
) -> None:
    """Assert that the ledger agrees with the per-position values on *date*."""
    positions = sim.bank.positions.open_positions()
    instruments = {p.id: sim.bank.instruments.get(p.instrument_id) for p in positions}

    def carrying(select: callable) -> dict[str, Decimal]:  # type: ignore[valid-type]
        return {
            p.id: _value(sim, p, date, ValuationType.CARRYING_VALUE)
            for p in positions
            if select(p, instruments[p.id])
        }

    if Check.BALANCE in checks:
        bs = ReportingService().balance_sheet(sim.bank.ledger, date=date)
        diff = Decimal(str(bs["total_assets"])) - Decimal(str(bs["total_liabilities"])) - Decimal(
            str(bs["total_equity"]),
        )
        if abs(diff) > _CENT:
            msg = f"BALANCE failed on {date}: assets - liabilities - equity = {diff:.2f}"
            raise AssertionError(msg)

    if Check.AMORTIZED_COST_SECURITIES in checks:
        parts = carrying(lambda p, i: p.measurement_basis == MeasurementBasis.AMORTIZED_COST and not _is_loan(i))
        name = "Investment Securities at Amortized Cost"
        _compare(Check.AMORTIZED_COST_SECURITIES, date, name, account_balance(sim, name), parts)

    if Check.FVOCI_SECURITIES in checks:
        parts = carrying(lambda p, _i: p.measurement_basis == MeasurementBasis.FVOCI)
        name = "Investment Securities at FVOCI"
        _compare(Check.FVOCI_SECURITIES, date, name, account_balance(sim, name), parts)

    if Check.FVTPL_ASSETS in checks:
        parts = carrying(lambda p, _i: p.measurement_basis == MeasurementBasis.FVTPL)
        name = "Assets at FVTPL"
        _compare(Check.FVTPL_ASSETS, date, name, account_balance(sim, name), parts)

    if Check.LOANS in checks:
        parts = carrying(lambda _p, i: _is_loan(i))
        name = "Loans and Advances"
        _compare(Check.LOANS, date, name, account_balance(sim, name), parts)

    if Check.ACCRUED_INTEREST in checks:
        name = "Accrued Interest Receivable"
        balance = account_balance(sim, name)
        if balance < -_CENT:
            msg = f"ACCRUED_INTEREST failed on {date}: {name} is negative ({balance:.2f})"
            raise AssertionError(msg)
        parts = {
            p.id: _value(sim, p, date, ValuationType.ACCRUED_INTEREST)
            for p in positions
            if p.side == PositionSide.LONG and getattr(instruments[p.id], "ql_instrument", None) is not None
        }
        _compare(Check.ACCRUED_INTEREST, date, name, balance, parts)

    if Check.DEPOSITS in checks:
        parts = {
            p.id: _value(sim, p, date, ValuationType.CARRYING_VALUE)
            for p in positions
            if getattr(instruments[p.id], "instrument_type", None) == InstrumentType.DEPOSIT
        }
        _compare(Check.DEPOSITS, date, "Deposits", account_balance(sim, "Deposits"), parts)

    if Check.INTEREST_PAYABLE in checks:
        parts = {
            p.id: _value(sim, p, date, ValuationType.ACCRUED_INTEREST)
            for p in positions
            if getattr(instruments[p.id], "instrument_type", None) == InstrumentType.DEPOSIT
        }
        name = "Interest Payable"
        _compare(Check.INTEREST_PAYABLE, date, name, account_balance(sim, name), parts)

    if Check.AOCI in checks:
        gain = account_balance(sim, "Unrealized OCI Gain")
        loss = account_balance(sim, "Unrealized OCI Loss")
        if gain > _CENT and loss > _CENT:
            msg = f"AOCI failed on {date}: both Unrealized OCI Gain ({gain:.2f}) and Loss ({loss:.2f}) are non-zero"
            raise AssertionError(msg)
        parts = {
            p.id: _value(sim, p, date, ValuationType.CARRYING_VALUE)
            - _value(sim, p, date, ValuationType.AMORTIZED_COST)
            for p in positions
            if p.measurement_basis == MeasurementBasis.FVOCI
        }
        _compare(Check.AOCI, date, "Unrealized OCI Gain - Loss", gain - loss, parts)
