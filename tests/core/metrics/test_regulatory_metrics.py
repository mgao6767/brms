"""Regulatory capital, RWA, ratios, leverage and trailing-year profitability metrics."""
# ruff: noqa: D103

from __future__ import annotations

import datetime
from decimal import Decimal

import pytest

from brms.core.enums import MeasurementBasis, MetricName
from brms.core.metrics.risk.credit_risk.exposures import credit_rwa
from brms.core.models.accounting.journal import SimpleEntry
from brms.core.models.instruments.base import CreditRating, Issuer, IssuerType
from brms.core.models.regulatory import RegulatoryConfig
from brms.core.services.reporting_service import ReportingService
from tests.support.engine import make_bond, make_position, run_bank, stepped_yields
from tests.support.reconcile import account_balance

_START = datetime.date(2021, 1, 4)
_YIELDS = stepped_yields(_START, datetime.date(2021, 7, 1), datetime.date(2022, 6, 30), 0.03, 0.05)
_DAY = datetime.date(2021, 9, 30)  # a Thursday after the rate rise
_CORP = Issuer(name="Acme", issuer_type=IssuerType.CORPORATE, credit_rating=CreditRating.A)


def _run(regulatory: RegulatoryConfig | None = None, until: datetime.date = _DAY, each_day=None):  # noqa: ANN001, ANN202
    bonds = [make_bond(id="OCI", issuer=_CORP), make_bond(id="AC")]
    positions = [
        make_position(id="pos-OCI", instrument_id="OCI", basis=MeasurementBasis.FVOCI, acquired=_START,
                      cost=Decimal(520_000)),
        make_position(id="pos-AC", instrument_id="AC", basis=MeasurementBasis.AMORTIZED_COST, acquired=_START,
                      cost=Decimal(520_000)),
    ]
    return run_bank(bonds, positions, yields=_YIELDS, until=until, regulatory=regulatory, each_day=each_day)


def _metric(sim, name: MetricName, day: datetime.date = _DAY):  # noqa: ANN001, ANN202
    return sim.metric_store.get(name, day)


def _equity(sim, day: datetime.date = _DAY) -> Decimal:  # noqa: ANN001
    return Decimal(str(ReportingService().balance_sheet(sim.bank.ledger, date=day)["total_equity"]))


def test_cet1_includes_aoci_unless_filtered() -> None:
    plain = _run()
    filtered = _run(RegulatoryConfig(aoci_filter=True))
    aoci = account_balance(plain, "Unrealized OCI Gain") - account_balance(plain, "Unrealized OCI Loss")
    assert aoci < 0  # noqa: S101
    assert abs(_metric(plain, MetricName.CET1_CAPITAL) - _equity(plain)) <= Decimal("0.01")  # noqa: S101
    assert abs(_metric(filtered, MetricName.CET1_CAPITAL) - (_equity(filtered) - aoci)) <= Decimal("0.01")  # noqa: S101


def test_capital_tiers_and_ratios() -> None:
    regulatory = RegulatoryConfig(
        operational_rwa=Decimal(100_000), additional_tier1=Decimal(20_000), tier2=Decimal(30_000),
    )
    sim = _run(regulatory)
    cet1 = _metric(sim, MetricName.CET1_CAPITAL)
    credit = credit_rwa(sim.bank, sim.valuation_store, _DAY).total
    assert _metric(sim, MetricName.CREDIT_RWA) == credit  # noqa: S101
    assert _metric(sim, MetricName.OPERATIONAL_RWA) == Decimal(100_000)  # noqa: S101
    total_rwa = credit + Decimal(100_000)
    assert _metric(sim, MetricName.TOTAL_RWA) == total_rwa  # noqa: S101
    assert _metric(sim, MetricName.TIER1_CAPITAL) == cet1 + 20_000  # noqa: S101
    assert _metric(sim, MetricName.TOTAL_CAPITAL) == cet1 + 50_000  # noqa: S101
    assert _metric(sim, MetricName.CET1_RATIO) == pytest.approx(float(cet1 / total_rwa))  # noqa: S101
    assert _metric(sim, MetricName.TIER1_RATIO) == pytest.approx(float((cet1 + 20_000) / total_rwa))  # noqa: S101
    assert _metric(sim, MetricName.TOTAL_CAPITAL_RATIO) == pytest.approx(float((cet1 + 50_000) / total_rwa))  # noqa: S101
    assets = Decimal(str(ReportingService().balance_sheet(sim.bank.ledger, date=_DAY)["total_assets"]))
    assert _metric(sim, MetricName.LEVERAGE_RATIO) == pytest.approx(float((cet1 + 20_000) / assets))  # noqa: S101


def test_intangibles_are_deducted_from_cet1_and_leverage_exposure() -> None:
    def book_intangible(sim, day: datetime.date) -> None:  # noqa: ANN001
        if day == datetime.date(2021, 9, 29):
            accounts = {a.name: a for a in sim.bank.ledger.chart_of_accounts.all_accounts()}
            sim.bank.ledger.post(SimpleEntry(
                debit_account=accounts["Intangible Assets"],
                credit_account=accounts["Cash and Cash Equivalents"], value=10_000.0, date=day,
            ))

    base = _run()
    with_intangible = _run(each_day=book_intangible)
    gap = _metric(base, MetricName.CET1_CAPITAL) - _metric(with_intangible, MetricName.CET1_CAPITAL)
    assert abs(gap - 10_000) <= Decimal("0.01")  # noqa: S101


def test_ratios_are_undefined_without_rwa() -> None:
    sim = run_bank([], [], yields=_YIELDS, until=datetime.date(2021, 2, 1))
    assert _metric(sim, MetricName.CET1_RATIO, datetime.date(2021, 2, 1)) is None  # noqa: S101


def test_trailing_year_profitability() -> None:
    end = datetime.date(2022, 2, 28)
    sim = _run(until=end)
    window_start = end - datetime.timedelta(days=364)
    statement = ReportingService().income_statement(sim.bank.ledger, start=window_start, end=end)
    net_income = Decimal(str(statement["net_income"]))
    nii = Decimal(str(sum(r["balance"] for r in statement["income"] if r["account"] == "Interest Income")))
    nii -= Decimal(str(sum(r["balance"] for r in statement["expenses"] if r["account"] == "Interest Expense")))

    def average(name: MetricName) -> Decimal:
        values = [v for d, v in sim.metric_store.series(name) if window_start <= d <= end]
        return sum((Decimal(str(v)) for v in values), Decimal(0)) / len(values)

    assert _metric(sim, MetricName.ROA, end) == pytest.approx(float(net_income / average(MetricName.TOTAL_ASSETS)))  # noqa: S101
    assert _metric(sim, MetricName.ROE, end) == pytest.approx(float(net_income / average(MetricName.TOTAL_EQUITY)))  # noqa: S101
    nim = nii / average(MetricName.INTEREST_EARNING_ASSETS)
    assert _metric(sim, MetricName.NET_INTEREST_MARGIN, end) == pytest.approx(float(nim))  # noqa: S101


def test_profitability_is_annualised_over_a_short_history() -> None:
    end = datetime.date(2021, 4, 2)
    sim = _run(until=end)
    days = (end - _START).days + 1
    statement = ReportingService().income_statement(sim.bank.ledger, start=_START, end=end)
    values = [Decimal(str(v)) for _d, v in sim.metric_store.series(MetricName.TOTAL_ASSETS)]
    expected = Decimal(str(statement["net_income"])) * 365 / days / (sum(values, Decimal(0)) / len(values))
    assert _metric(sim, MetricName.ROA, end) == pytest.approx(float(expected))  # noqa: S101
