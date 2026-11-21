"""Build small banks in tests and run them day by day with reconciliation."""

from __future__ import annotations

import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

import pandas as pd

from brms.core.enums import BookType, MeasurementBasis, PositionSide
from brms.core.models.instruments import default_instrument_registry
from brms.core.models.instruments.base import CreditRating, Issuer, IssuerType
from brms.core.models.instruments.equity import CommonEquity
from brms.core.models.operating import OperatingConfig
from brms.core.models.position import Position
from brms.core.models.regulatory import RegulatoryConfig
from brms.core.services.simulation_builder import BuildConfig, SimulationBuilder
from brms.core.utils import pydate_to_qldate
from tests.support.reconcile import Check, assert_books_reconcile

if TYPE_CHECKING:
    from collections.abc import Callable

    from brms.core.models.instruments.base import Instrument
    from brms.core.services.simulation_service import SimulationService

TENORS = ("1 Mo", "2 Mo", "3 Mo", "4 Mo", "6 Mo", "1 Yr", "2 Yr", "3 Yr", "5 Yr", "7 Yr", "10 Yr", "20 Yr", "30 Yr")

# Reference bond R used across the correct-books tests.
R_FACE = 500_000.0
R_COUPON = 0.05
R_ISSUE = datetime.date(2020, 7, 1)
R_MATURITY = datetime.date(2022, 7, 1)
FUNDING_DATE = datetime.date(2021, 1, 4)
FUNDING = Decimal(2_000_000)
_SOVEREIGN = object()  # sentinel: make_bond's default issuer


def flat_yields(start: datetime.date, end: datetime.date, rate: float = 0.03) -> pd.DataFrame:
    """Return a yields frame with every tenor at *rate*, on business days (percent, like yields.csv)."""
    index = pd.bdate_range(start, end, name="date")
    return pd.DataFrame({t: rate * 100 for t in TENORS}, index=index)


def stepped_yields(
    start: datetime.date, step: datetime.date, end: datetime.date, before: float, after: float,
) -> pd.DataFrame:
    """Return flat yields at *before* until *step* (exclusive), then *after*."""
    first = flat_yields(start, step - datetime.timedelta(days=1), before)
    second = flat_yields(step, end, after)
    return pd.concat([first, second])


def make_bond(  # noqa: PLR0913
    *,
    id: str,  # noqa: A002
    face: float = R_FACE,
    coupon: float = R_COUPON,
    issue: datetime.date = R_ISSUE,
    maturity: datetime.date = R_MATURITY,
    registry_type: str = "treasury_note",
    issuer: Issuer | None | object = _SOVEREIGN,
) -> Instrument:
    """Build a fixed-rate bond through the default registry (issuer: US sovereign, AAA, by default)."""
    if issuer is _SOVEREIGN:
        issuer = Issuer(name="US Government", issuer_type=IssuerType.SOVEREIGN, credit_rating=CreditRating.AAA)
    bond = default_instrument_registry().create(
        registry_type,
        face_value=face,
        coupon_rate=coupon,
        issue_date=pydate_to_qldate(issue),
        maturity_date=pydate_to_qldate(maturity),
        issuer=issuer,
    )
    bond.id = id
    return bond


def make_position(  # noqa: PLR0913
    *,
    id: str,  # noqa: A002
    instrument_id: str,
    basis: MeasurementBasis,
    acquired: datetime.date,
    cost: Decimal,
    book: BookType = BookType.BANKING,
    side: PositionSide = PositionSide.LONG,
) -> Position:
    """Build a position."""
    return Position(
        id=id,
        instrument_id=instrument_id,
        book_type=book,
        measurement_basis=basis,
        side=side,
        acquisition_date=acquired,
        acquisition_cost=Decimal(cost),
    )


def funding(
    acquired: datetime.date = FUNDING_DATE, amount: Decimal = FUNDING,
) -> tuple[list[Instrument], list[Position]]:
    """Return an equity instrument and SHORT position so the bank has cash."""
    equity = CommonEquity(name="Test equity")
    equity.id = "equity"
    position = make_position(
        id="pos-equity",
        instrument_id="equity",
        basis=MeasurementBasis.NA,
        acquired=acquired,
        cost=amount,
        side=PositionSide.SHORT,
    )
    return [equity], [position]


def run_bank(  # noqa: PLR0913
    instruments: list[Instrument],
    positions: list[Position],
    *,
    yields: pd.DataFrame,
    until: datetime.date,
    checks: frozenset[Check] = frozenset(Check),
    each_day: Callable[[SimulationService, datetime.date], None] | None = None,
    with_funding: bool = True,
    regulatory: RegulatoryConfig | None = None,
    reinvest_maturities: bool = False,
    calibrate_spreads: bool = False,
    operating: OperatingConfig | None = None,
) -> SimulationService:
    """Replay the bank day by day through *until*, reconciling after every advance."""
    if with_funding:
        eq_instruments, eq_positions = funding()
        instruments = [*eq_instruments, *instruments]
        positions = [*eq_positions, *positions]

    def on_advance(sim: SimulationService, day: datetime.date) -> None:
        assert_books_reconcile(sim, day, checks)
        if each_day is not None:
            each_day(sim, day)

    config = BuildConfig(
        name="test bank",
        start_date=until + datetime.timedelta(days=1),
        instruments=instruments,
        positions=positions,
        market_frames={"yields": yields},
        regulatory=regulatory or RegulatoryConfig(),
        reinvest_maturities=reinvest_maturities,
        calibrate_spreads=calibrate_spreads,
        operating=operating or OperatingConfig(),
    )
    return SimulationBuilder().replay(config, until=until, on_advance=on_advance)
