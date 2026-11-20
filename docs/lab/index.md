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

Agency mortgage-backed securities are pass-through pools:

```json
{"id": "mbs", "type": "mortgage_backed_security", "face_value": 600000, "coupon_rate": 0.02,
 "wac": 0.025, "issue_date": "2021-12-31", "maturity": "25Y",
 "issuer": {"name": "Agency", "issuer_type": "PSE", "credit_rating": "AA_PLUS"},
 "basis": "AMORTIZED_COST", "amortized_cost": 600000, "fair_value": 590000,
 "prepayment": {"turnover_cpr": 0.06, "max_cpr": 0.5, "refi_center": 0.0075, "refi_width": 0.0075,
                "mortgage_spread": 0.017}}
```

The annual prepayment rate (CPR) is an S-curve in the refinancing incentive: the note rate (`wac`,
default coupon + 0.5%) less the mortgage rate, taken as the 10-year Treasury zero rate plus
`mortgage_spread`. Fair value and EVE project the remaining cash flows at today's speed, so a
rate rise slows prepayment and lengthens the pool, and a rate fall caps its gains. Realised
paydowns, which drive the cash and the books, follow a constant `pricing_cpr`. It defaults to the
model's speed on the as-of date. Pools must be bought at par and held at `AMORTIZED_COST` or
`FVOCI`. Every field of `prepayment` is optional.

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
  spread. Mortgage-backed securities project prepayments from rates, but their realised paydowns
  follow a fixed speed, so the cash available to reinvest does not respond to rates.
- Standardised approaches only: CRE20 credit risk, SRP31 interest-rate shocks; operational RWA,
  AT1 and Tier 2 are inputs.
- Deposits reprice overnight for EVE and NII sensitivity.

See [the SVB case](svb.md) for how close this gets on a real bank, and [Call Reports](call_report.md)
to load any US bank from its regulatory filing.
