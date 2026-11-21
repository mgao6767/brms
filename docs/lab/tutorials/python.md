# Python and the command line

Everything the browser app does is available from Python, for notebooks, research and batch runs,
and from the command line.

## Run a scenario

```python
from brms.data import DEFAULT_DATA_FOLDER
from brms.lab import Historical, run

svb = DEFAULT_DATA_FOLDER.parent / "case_svb_2021.zip"   # a shipped case study
result = run(svb, Historical(), months=12)
print(result.summary)
```

`run(simulation, scenario, ...)` takes a simulation zip (shipped, or built with `build_bank`) and:

| Argument | Meaning |
|---|---|
| `months` | horizon from the start date, e.g. `months=12`; or give `end=datetime.date(...)`. With neither, the run goes to the end of the simulation's market data |
| `regulatory` | a `RegulatoryConfig` (`brms.core.models.regulatory`) overriding the AOCI filter, operational RWA, AT1 and Tier 2; default: the bank's own |
| `operating` | an `OperatingConfig` (`brms.core.models.operating`) overriding costs, fees, tax rate and dividend payout; default: the bank's own |
| `sales` | `{"pos-afs": date}`: sell positions at fair value on market days (AFS and trading positions only); default none |
| `reinvest_maturities` | `True` rolls each maturing bond into a new par bond of the same term at the market rate; default `False` (maturities stay in cash) |

To switch the AOCI filter off while keeping the bank's other settings:

```python
import dataclasses
from brms.core.services import build_core_services

regulatory = dataclasses.replace(build_core_services(simulation_zip=svb).bank.regulatory, aoci_filter=False)
counted = run(svb, Historical(), months=12, regulatory=regulatory)
```

## Scenarios

```python
from brms.core.metrics.risk.interest_rate_risk.eve import Scenario
from brms.lab import Historical, KeyRateShift, Shock

Historical()                                   # the stored Treasury yields and Prime rate
Shock(Scenario.PARALLEL_UP)                    # +200bp from the start date
Shock(Scenario.STEEPENER, ramp_days=90)        # phased in over 90 days
Shock(KeyRateShift(((0.25, 300), (2, 200), (10, 50))), label="bear flattener")   # bp by maturity (years)
Shock(Scenario.PARALLEL_DOWN, floor=0.0)       # yields floored at 0%
```

The six Basel scenarios are `PARALLEL_UP`, `PARALLEL_DOWN`, `STEEPENER`, `FLATTENER`, `SHORT_UP`
and `SHORT_DOWN`. See [Scenarios](../guides/scenarios.md) for the shapes and how a shock moves
the Prime rate.

## Many scenarios at once

```python
from brms.lab import run_many

results = run_many(svb, [Historical(), Shock(Scenario.PARALLEL_UP), Shock(Scenario.STEEPENER)],
                   months=12, workers=4)
```

Each scenario runs in its own process, in parallel. Put the call under
`if __name__ == "__main__":` in scripts, as for any Python multiprocessing code.

## What a run returns

A `RunResult` holds plain pandas data:

| Attribute | Contents |
|---|---|
| `metrics` | one row per market day, one column per [metric](../reference/metrics.md): `CET1_RATIO`, `LEVERAGE_RATIO`, `DELTA_EVE_WORST_TO_TIER1`, `ASSET_DURATION`, … |
| `carrying_value`, `fair_value`, `amortized_cost` | one row per day, one column per position id |
| `statements` | balance sheet and income statement (since the start) per market day, long form: `date`, `section`, `account`, `balance` |
| `journal` | every journal line: `date`, `entry`, `kind`, `description`, `position`, `account`, `debit`, `credit` |
| `positions` | every position: `id`, `instrument`, `name`, `type`, `basis`, `book`, `side`, `status` |
| `yields` | the scenario's Treasury curve (percent) |
| `balance_sheet`, `income_statement` | the statements on the last day, as dictionaries |
| `summary` | headline numbers: CET1 at the end and its low point, worst ΔEVE/Tier 1, net income, and `unrealised_end` (HTM, AFS and loans on the last market day) |
| `unrealised(position_id)` | fair value less amortised cost on the last day both exist |

Fair values exist only on market days (business days with a Treasury curve), while carrying value
and amortised cost exist every calendar day. Take the last market day with
`.dropna(how="all").iloc[-1]` when you combine them.

Examples:

```python
result.metrics["CET1_RATIO"].plot()                    # with matplotlib installed

# unrealised gain or loss of every HTM security on the last day
securities = ["FIXED_RATE_BOND", "TREASURY_NOTE", "TREASURY_BOND", "MORTGAGE_BACKED_SECURITY"]
held = result.positions[(result.positions["basis"] == "AMORTIZED_COST") & result.positions["type"].isin(securities)]
gap = (result.fair_value - result.amortized_cost).dropna(how="all")[held["id"]].iloc[-1].dropna()
print(gap.sum(), result.summary["unrealised_end"]["htm"])   # the same total

# the balance sheet on 30 June 2022
import datetime
s = result.statements
s[(s["date"] == datetime.date(2022, 6, 30)) & s["section"].isin(["assets", "liabilities", "equity"])]

# every entry booked for one position
result.journal[result.journal["position"] == "pos-pt-ov15-htm"]
```

## Build banks

```python
from pathlib import Path
from brms.lab.bank_file import build_bank, default_market_frames

simulation = build_bank(Path("riverside.json"), default_market_frames(), Path("riverside.zip"))
```

`default_market_frames()` returns the Treasury yields and Prime rate shipped with the package
(daily, from 1990 to the end of 2025). To use your own, pass `{"yields": df, "benchmarks": df}`
with the same columns (Treasury CMT tenors such as `"3 Mo"`, `"10 Yr"`, in percent; `DPRIME`).

From a Call Report: see [the Call Report tutorial](call-report.md#from-python-or-the-command-line).

## The command line

```bash
python -m brms.lab call-report --cert 24735 --date 2021-12-31 --out svb.json \
    [--ltv 0.8] [--deposit-beta 0.35] [--no-aoci-filter] [--no-core-deposits]
python -m brms.lab build-bank svb.json --out svb.zip [--yields yields.csv] [--benchmarks prime.csv]
python -m brms.lab run svb.zip --scenario historical --scenario parallel+200 \
    [--months 12] [--workers 4] [--out results]
```

Scenario names for `run`: `historical`, `parallel+200`, `parallel-200`, `steepener`, `flattener`,
`short+300`, `short-300`, or any parallel shift such as `parallel+150` or `parallel-50`.
`run` prints a summary table and writes, for each scenario, a folder under `--out` named after the
scenario (`historical`, `parallel_up`, `parallel_down`, `steepener`, `flattener`, `short_up`,
`short_down`, `parallel+150bp`…) holding `metrics.csv`, `carrying_value.csv`, `fair_value.csv` and
`summary.json`. Sales and reinvestment are available from Python, not from the command line.

`brms-web [--port 8765] [--host 127.0.0.1] [--data-dir DIR] [--workers 2] [--no-browser]` starts the
browser app.
