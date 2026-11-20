"""Snapshots: closed books, all four valuations, position status, and a faithful round trip."""
# ruff: noqa: D103

from __future__ import annotations

import datetime
from decimal import Decimal
from pathlib import Path

import pytest

from brms.core.enums import BookType, MeasurementBasis, PositionSide, PositionStatus, TransactionType, ValuationType
from brms.core.exceptions import SimulationDataError
from brms.core.models.accounting.accounts import AccountType
from brms.core.models.instruments import default_instrument_registry
from brms.core.models.position import Position
from brms.core.rules.interest_accrual import scaled_accrued_amount
from brms.core.services import build_core_services
from brms.core.services.data_service import _convert_kwargs
from brms.core.services.reporting_service import ReportingService
from brms.core.services.simulation_builder import BuildConfig, SimulationBuilder, outstanding_principal
from brms.core.services.snapshot_writer import save_snapshot
from brms.core.utils import pydate_to_qldate
from tests.support.engine import flat_yields
from tests.support.reconcile import assert_books_reconcile

_START = datetime.date(2021, 6, 1)
_END = datetime.date(2021, 8, 31)
_LEGACY = Path(__file__).resolve().parents[2] / "fixtures" / "legacy" / "htm_treasury_pre_correct_books.zip"

_GOV = {"name": "US Government", "issuer_type": "SOVEREIGN", "credit_rating": "AAA"}

_SPECS: list[dict[str, object]] = [
    {"id": "equity", "type": "common_equity", "name": "Equity"},
    {"id": "deposit", "type": "deposit", "name": "Savings", "interest_rate": 0.01},
    *[
        {
            "id": f"R-{basis}", "type": "treasury_note", "face_value": 500_000.0, "coupon_rate": 0.05,
            "issue_date": "2020-07-01", "maturity_date": "2022-07-01", "issuer": _GOV,
        }
        for basis in ("AMORTIZED_COST", "FVOCI", "FVTPL")
    ],
    {
        "id": "short", "type": "treasury_note", "face_value": 100_000.0, "coupon_rate": 0.02,
        "issue_date": "2020-03-01", "maturity_date": "2021-03-01", "issuer": _GOV,
    },
    {
        "id": "M", "type": "residential_mortgage", "face_value": 300_000.0, "interest_rate": 0.06,
        "issue_date": "2020-12-15", "maturity": "1Y", "ltv": 0.7,
    },
]


def _instruments() -> dict[str, object]:
    registry = default_instrument_registry()
    built = {}
    for spec in _SPECS:
        kwargs = dict(spec)
        type_id, iid = kwargs.pop("type"), kwargs.pop("id")
        name = kwargs.pop("name", None)
        inst = registry.create(type_id, **_convert_kwargs(kwargs))
        inst.id = iid
        if name:
            inst.name = name
        built[iid] = inst
    return built


def _position(pid: str, iid: str, basis: MeasurementBasis, acquired: datetime.date, cost: Decimal, side=PositionSide.LONG):  # noqa: ANN001, ANN202, E501, PLR0913
    return Position(
        id=pid, instrument_id=iid, book_type=BookType.BANKING, measurement_basis=basis, side=side,
        acquisition_date=acquired, acquisition_cost=cost,
    )


def _config() -> BuildConfig:
    inst = _instruments()
    bought = datetime.date(2021, 1, 4)
    mortgage_day = datetime.date(2021, 1, 20)
    mortgage_cost = outstanding_principal(inst["M"], mortgage_day) + scaled_accrued_amount(
        inst["M"].ql_instrument, pydate_to_qldate(mortgage_day),
    )
    short_accrued = scaled_accrued_amount(inst["short"].ql_instrument, pydate_to_qldate(bought))
    positions = [
        _position("pos-equity", "equity", MeasurementBasis.NA, bought, Decimal(3_000_000), PositionSide.SHORT),
        _position("pos-deposit", "deposit", MeasurementBasis.NA, bought, Decimal(1_000_000), PositionSide.SHORT),
        _position("pos-AC", "R-AMORTIZED_COST", MeasurementBasis.AMORTIZED_COST, bought, Decimal(520_000)),
        _position("pos-OCI", "R-FVOCI", MeasurementBasis.FVOCI, bought, Decimal(520_000)),
        _position("pos-TPL", "R-FVTPL", MeasurementBasis.FVTPL, bought, Decimal(520_000)),
        _position("pos-short", "short", MeasurementBasis.AMORTIZED_COST, bought, Decimal(100_000) + short_accrued),
        _position("pos-M", "M", MeasurementBasis.AMORTIZED_COST, mortgage_day, mortgage_cost),
    ]
    return BuildConfig(
        name="round trip", start_date=_START, instruments=list(inst.values()), positions=positions,
        market_frames={"yields": flat_yields(datetime.date(2021, 1, 4), _END)},
    )


@pytest.fixture(scope="module")
def saved(tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = tmp_path_factory.mktemp("snap") / "bank.zip"
    save_snapshot(SimulationBuilder().build(_config()), _SPECS, path, end_date=_END)
    return path


def _income_expense_names() -> set[str]:
    from brms.core.models.accounting.bank_accounts import BankChartOfAccounts

    return {a.name for a in BankChartOfAccounts().all_accounts() if a.type in (AccountType.INCOME, AccountType.EXPENSE)}


def test_snapshot_has_no_income_or_expense_balances() -> None:
    snapshot = SimulationBuilder().build(_config())
    assert not set(snapshot.balances) & _income_expense_names()  # noqa: S101
    assert {"carrying_value", "amortized_cost", "accrued_interest"} <= set(snapshot.valuations["pos-OCI"])  # noqa: S101


def test_roundtrip_matches_continued_replay(saved: Path) -> None:
    continued = SimulationBuilder().replay(_config(), until=_END)
    loaded = build_core_services(simulation_zip=saved).simulation_service
    day = _START
    while day <= _END:
        loaded.advance(day)
        assert_books_reconcile(loaded, day)
        day += datetime.timedelta(days=1)
    reporting = ReportingService()
    a = reporting.balance_sheet(continued.bank.ledger, date=_END)
    b = reporting.balance_sheet(loaded.bank.ledger, date=_END)
    rows_a = {r["account"]: r["balance"] for r in a["assets"] + a["liabilities"] + a["equity"]}
    rows_b = {r["account"]: r["balance"] for r in b["assets"] + b["liabilities"] + b["equity"]}
    for name in rows_a.keys() | rows_b.keys():
        assert abs(rows_a.get(name, 0.0) - rows_b.get(name, 0.0)) <= 0.01, name  # noqa: S101, PLR2004


def test_position_matured_before_snapshot_stays_closed(saved: Path) -> None:
    sim = build_core_services(simulation_zip=saved).simulation_service
    assert sim.bank.positions.get("pos-short").status == PositionStatus.CLOSED  # noqa: S101
    sim.advance(_START)
    assert not [t for t in sim.transaction_log.all() if t.type == TransactionType.MATURITY_SETTLEMENT]  # noqa: S101


def test_income_statement_starts_at_zero_after_load(saved: Path) -> None:
    services = build_core_services(simulation_zip=saved)
    statement = services.reporting_service.income_statement(services.bank.ledger)
    assert statement["total_income"] == 0  # noqa: S101
    assert statement["total_expenses"] == 0  # noqa: S101


def test_old_format_zip_is_rejected_clearly() -> None:
    with pytest.raises(SimulationDataError, match="regenerate"):
        build_core_services(simulation_zip=_LEGACY)


def _read_json(path: Path, name: str) -> dict:
    import json
    import zipfile

    with zipfile.ZipFile(path) as zf:
        return json.loads(zf.read(name))


def test_snapshot_records_its_format_and_snapshot_date(saved: Path) -> None:
    assert _read_json(saved, "config.json")["format"] == 2  # noqa: S101, PLR2004
    assert _read_json(saved, "balances.json")["snapshot_date"] == (_START - datetime.timedelta(days=1)).isoformat()  # noqa: S101


def test_zip_without_current_format_is_rejected(saved: Path, tmp_path: Path) -> None:
    import json
    import zipfile

    stale = tmp_path / "stale.zip"
    with zipfile.ZipFile(saved) as zin, zipfile.ZipFile(stale, "w") as zout:
        for name in zin.namelist():
            data = zin.read(name)
            if name == "config.json":
                config = json.loads(data)
                config.pop("format")
                data = json.dumps(config).encode()
            zout.writestr(name, data)
    with pytest.raises(SimulationDataError, match="regenerate"):
        build_core_services(simulation_zip=stale)


def test_loading_does_not_value_the_start_date_before_it_is_processed(saved: Path) -> None:
    services = build_core_services(simulation_zip=saved)
    assert services.valuation_store.snapshot(_START, ValuationType.CARRYING_VALUE) == {}  # noqa: S101
    snapshot_day = _START - datetime.timedelta(days=1)
    assert services.valuation_store.snapshot(snapshot_day, ValuationType.CARRYING_VALUE)  # noqa: S101
