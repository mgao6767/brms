"""Run a simulation through a scenario, in this process or one process per scenario."""

from __future__ import annotations

import datetime
import re
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pandas as pd
from dateutil.relativedelta import relativedelta

from brms.core.enums import EntryKind, MetricName, ValuationType
from brms.core.results import metrics_frame, valuations_frame
from brms.core.services import build_core_services

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from brms.core.models.operating import OperatingConfig
    from brms.core.models.regulatory import RegulatoryConfig
    from brms.core.services import CoreServices
    from brms.lab.scenarios import Historical, Shock


@dataclass(frozen=True)
class RunResult:
    """Everything a scenario run produced, as plain picklable data."""

    name: str
    start: datetime.date
    end: datetime.date
    metrics: pd.DataFrame
    carrying_value: pd.DataFrame
    fair_value: pd.DataFrame
    amortized_cost: pd.DataFrame
    balance_sheet: dict[str, Any]
    income_statement: dict[str, Any]
    transactions: int
    # Long form, one row per line item and market day: date, section (assets, liabilities, equity,
    # income, expenses, totals), account, balance. Income and expenses run from the start date.
    statements: pd.DataFrame
    # One row per journal line from the start date: date, entry, kind, description, account, debit, credit.
    journal: pd.DataFrame
    # Every position held during the run: id, instrument, name, type, basis, book, side, status.
    positions: pd.DataFrame
    # The scenario's Treasury CMT yields (percent) on market days from the start date.
    yields: pd.DataFrame

    def unrealised(self, position_id: str) -> float | None:
        """Fair value less amortised cost of a position on the last day both are recorded."""
        if position_id not in self.fair_value or position_id not in self.amortized_cost:
            return None
        both = (self.fair_value[position_id] - self.amortized_cost[position_id]).dropna()
        return None if both.empty else float(both.iloc[-1])

    @property
    def summary(self) -> dict[str, Any]:
        """Headline numbers: end and minimum CET1 ratio, worst ΔEVE/Tier 1, net income."""
        cet1 = self.metrics.get(MetricName.CET1_RATIO.name)
        eve = self.metrics.get(MetricName.DELTA_EVE_WORST_TO_TIER1.name)
        cet1 = cet1.dropna() if cet1 is not None else None
        return {
            "scenario": self.name,
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "cet1_ratio_end": None if cet1 is None or cet1.empty else float(cet1.iloc[-1]),
            "cet1_ratio_min": None if cet1 is None or cet1.empty else float(cet1.min()),
            "cet1_ratio_min_date": None if cet1 is None or cet1.empty else cet1.idxmin().date().isoformat(),
            "worst_delta_eve_to_tier1": None if eve is None or eve.dropna().empty else float(eve.dropna().min()),
            "net_income": float(self.income_statement["net_income"]),
            "total_assets_end": float(self.balance_sheet["total_assets"]),
            "total_equity_end": float(self.balance_sheet["total_equity"]),
        }


def run(  # noqa: PLR0913
    simulation: Path | str,
    scenario: Historical | Shock,
    *,
    months: int | None = None,
    end: datetime.date | None = None,
    regulatory: RegulatoryConfig | None = None,
    operating: OperatingConfig | None = None,
    sales: Mapping[str, datetime.date] | None = None,
    reinvest_maturities: bool = False,
) -> RunResult:
    """Run *simulation* (a snapshot zip) through *scenario* from its start date.

    The horizon ends at *end*, else *months* after the start, else the archive's end date.
    *regulatory* and *operating* override the archive's regulatory and operating inputs.
    *sales* maps position ids to the
    market day on which to sell them at fair value (FVOCI and FVTPL positions).
    With *reinvest_maturities*, maturing bonds roll into new par bonds of the same term.
    """
    services = build_core_services(simulation_zip=Path(simulation))
    sim = services.simulation_service
    if regulatory is not None:
        services.bank.regulatory = regulatory
    if operating is not None:
        services.bank.operating = operating
    services.bank.reinvest_maturities = reinvest_maturities
    for position_id, day in (sales or {}).items():
        services.bank.positions.get(position_id).sale_date = day
    start = sim.start_date
    if end is None:
        end = start + relativedelta(months=months) - datetime.timedelta(days=1) if months else sim.end_date
    for name, frame in scenario.frames(services.market_data, start, end).items():
        services.market_data.add_frame(name, frame)
    sim.end_date = end
    statements: list[pd.DataFrame] = []
    while sim.current_date < end:
        sim.advance()
        if sim.market_data.has_data(sim.current_date):
            statements.append(_statements(services, sim.current_date))
    reporting = services.reporting_service
    return RunResult(
        name=scenario.name,
        start=start,
        end=end,
        metrics=metrics_frame(services.metric_store),
        carrying_value=valuations_frame(services.valuation_store, ValuationType.CARRYING_VALUE),
        fair_value=valuations_frame(services.valuation_store, ValuationType.FAIR_VALUE),
        amortized_cost=valuations_frame(services.valuation_store, ValuationType.AMORTIZED_COST),
        balance_sheet=reporting.balance_sheet(services.bank.ledger, date=end),
        income_statement=reporting.income_statement(services.bank.ledger, start=start, end=end),
        transactions=len(services.transaction_log.all()),
        statements=pd.concat(statements, ignore_index=True) if statements else _statements(services, start),
        journal=_journal(services, start),
        positions=_positions(services),
        yields=services.market_data.get_frame("yields").loc[pd.Timestamp(start): pd.Timestamp(end)].copy(),
    )


_TOTALS = ("total_assets", "total_liabilities", "total_equity", "total_income", "total_expenses", "net_income")


def _statements(services: CoreServices, day: datetime.date) -> pd.DataFrame:
    """Return the balance sheet on *day* and the income statement since *start*, in long form."""
    reporting = services.reporting_service
    sheet = reporting.balance_sheet(services.bank.ledger, date=day)
    # The builder closes the books the day before the start and a run never closes them again, so
    # the current income and expense balances are the profit since the start (and far cheaper to
    # read daily than a windowed statement).
    income = reporting.income_statement(services.bank.ledger)
    rows = [
        (day, section, line["account"], float(line["balance"]))
        for source, sections in ((sheet, ("assets", "liabilities", "equity")), (income, ("income", "expenses")))
        for section in sections
        for line in source[section]
    ]
    merged = {**sheet, **income}
    rows += [(day, "totals", key, float(merged[key])) for key in _TOTALS]
    return pd.DataFrame(rows, columns=["date", "section", "account", "balance"])


_TX_REF = re.compile(r"\s*\(tx=([0-9a-f-]+)\)")


def _journal(services: CoreServices, start: datetime.date) -> pd.DataFrame:
    """Return every journal line posted from *start* (opening entries excluded).

    Each line carries the position whose transaction produced the entry (None for entries that
    belong to no position); the transaction reference is taken out of the description.
    """
    owners = {t.id: t.position_id for t in services.transaction_log.all()}
    rows = []
    for number, entry in enumerate(services.bank.ledger.journal.entries):
        if entry.date is None or entry.date < start or entry.kind == EntryKind.OPENING:
            continue
        reference = _TX_REF.search(entry.description)
        description = _TX_REF.sub("", entry.description)
        position = owners.get(reference.group(1)) if reference else None
        head = (entry.date, number, entry.kind.name, description, position)
        rows += [(*head, account.name, float(value), 0.0) for account, value in entry.debit_account_value_pairs()]
        rows += [(*head, account.name, 0.0, float(value)) for account, value in entry.credit_account_value_pairs()]
    columns = ["date", "entry", "kind", "description", "position", "account", "debit", "credit"]
    return pd.DataFrame(rows, columns=columns)


def _positions(services: CoreServices) -> pd.DataFrame:
    """Return static facts about every position (open or closed)."""
    rows = []
    for position in services.bank.positions.query():
        instrument = services.bank.instruments.get(position.instrument_id)
        kind = getattr(instrument, "instrument_type", None)
        rows.append({
            "id": position.id, "instrument": position.instrument_id, "name": instrument.name,
            "type": kind.name if kind is not None else "", "basis": position.measurement_basis.name,
            "book": position.book_type.name, "side": position.side.name, "status": position.status.name,
        })
    return pd.DataFrame(rows, columns=["id", "instrument", "name", "type", "basis", "book", "side", "status"])


def _run_one(args: tuple[Path, Historical | Shock, dict[str, Any]]) -> RunResult:
    simulation, scenario, kwargs = args
    return run(simulation, scenario, **kwargs)


def run_many(
    simulation: Path | str,
    scenarios: Sequence[Historical | Shock],
    *,
    workers: int | None = None,
    **kwargs: Any,  # noqa: ANN401
) -> list[RunResult]:
    """Run each scenario in its own worker process and return the results in input order.

    One scenario per process keeps QuantLib's process-wide state (evaluation date, index
    fixings) from mixing between scenarios. Scenarios must be picklable (named functions, not
    lambdas, as custom shock shapes).
    """
    jobs = [(Path(simulation), scenario, kwargs) for scenario in scenarios]
    with ProcessPoolExecutor(max_workers=workers, max_tasks_per_child=1) as pool:
        return list(pool.map(_run_one, jobs))
