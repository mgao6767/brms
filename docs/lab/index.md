# Stress-test lab

BRMS runs a bank's balance sheet through interest-rate scenarios with full double-entry accounting,
and reports statements, regulatory capital and interest-rate risk every day.

## Install

```bash
pip install brms          # headless library and lab
pip install "brms[gui]"   # plus the desktop app
```

## Describe a bank

A bank file lists positions as of one date: instrument terms, issuer, accounting basis, and clean
amortised cost and/or fair value. Each position's credit spread is calibrated to its reported fair
value; equity is the balancing figure. Deposits can pass through part of market-rate rises (`beta`),
run off (`runoff_rate`) or suffer scheduled withdrawals.

```bash
python -m brms.lab build-bank bank.json --out bank.zip
```

## Run scenarios

```bash
python -m brms.lab run bank.zip --scenario historical --scenario parallel+200 \
    --scenario steepener --months 12 --out results
```

Each scenario writes `metrics.csv` (CET1, Tier 1 and Total capital ratios, leverage ratio, credit
RWA, EVE and worst ΔEVE under the six Basel shocks, duration, NII sensitivity, ROA, ROE, NIM and
more), position valuations and a `summary.json`. Scenarios run in separate processes.

From Python:

```python
from brms.lab import run, Shock
from brms.core.metrics.risk.interest_rate_risk.eve import Scenario
from brms.core.models.regulatory import RegulatoryConfig

result = run("bank.zip", Shock(Scenario.PARALLEL_UP, ramp_days=90), months=12,
             regulatory=RegulatoryConfig(aoci_filter=True),
             sales={"pos-afs": date(2023, 3, 8)}, reinvest_maturities=True)
result.metrics["CET1_RATIO"].plot()
```

## What the engine assumes

- Valuation by discounting each position's cash flows on the Treasury curve plus a constant credit
  spread; no prepayment model (mortgage-backed securities do not extend as rates rise).
- Standardised approaches only: CRE20 credit risk, SRP31 interest-rate shocks; operational RWA,
  AT1 and Tier 2 are inputs.
- Deposits reprice overnight for EVE and NII sensitivity.

See [the SVB case](svb.md) for how close this gets on a real bank.
