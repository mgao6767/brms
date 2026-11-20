"""Run a simulation through a scenario, in this process or one process per scenario."""

from __future__ import annotations

import datetime
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from dateutil.relativedelta import relativedelta

from brms.core.enums import MetricName, ValuationType
from brms.core.results import metrics_frame, valuations_frame
from brms.core.services import build_core_services

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    import pandas as pd

    from brms.core.models.regulatory import RegulatoryConfig
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
    balance_sheet: dict[str, Any]
    income_statement: dict[str, Any]
    transactions: int

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
    sales: Mapping[str, datetime.date] | None = None,
    reinvest_maturities: bool = False,
) -> RunResult:
    """Run *simulation* (a snapshot zip) through *scenario* from its start date.

    The horizon ends at *end*, else *months* after the start, else the archive's end date.
    *regulatory* overrides the archive's regulatory inputs. *sales* maps position ids to the
    market day on which to sell them at fair value (FVOCI and FVTPL positions).
    With *reinvest_maturities*, maturing bonds roll into new par bonds of the same term.
    """
    services = build_core_services(simulation_zip=Path(simulation))
    sim = services.simulation_service
    if regulatory is not None:
        services.bank.regulatory = regulatory
    services.bank.reinvest_maturities = reinvest_maturities
    for position_id, day in (sales or {}).items():
        services.bank.positions.get(position_id).sale_date = day
    start = sim.start_date
    if end is None:
        end = start + relativedelta(months=months) - datetime.timedelta(days=1) if months else sim.end_date
    for name, frame in scenario.frames(services.market_data, start, end).items():
        services.market_data.add_frame(name, frame)
    sim.end_date = end
    while sim.current_date < end:
        sim.advance()
    reporting = services.reporting_service
    return RunResult(
        name=scenario.name,
        start=start,
        end=end,
        metrics=metrics_frame(services.metric_store),
        carrying_value=valuations_frame(services.valuation_store, ValuationType.CARRYING_VALUE),
        fair_value=valuations_frame(services.valuation_store, ValuationType.FAIR_VALUE),
        balance_sheet=reporting.balance_sheet(services.bank.ledger, date=end),
        income_statement=reporting.income_statement(services.bank.ledger, start=start, end=end),
        transactions=len(services.transaction_log.all()),
    )


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
