# Metrics

Computed on every market day and returned in `RunResult.metrics` (Python), `metrics.csv` (command
line) and **Download CSV → Metrics, daily** (browser). Money is in the bank's unit; ratios are
fractions (0.12 = 12%).

## Balance sheet

| Column | Definition |
|---|---|
| `TOTAL_ASSETS` | total assets of the balance sheet (as if the books were closed that day) |
| `TOTAL_LIABILITIES` | total liabilities |
| `TOTAL_EQUITY` | total equity |
| `EQUITY_TO_ASSETS` | total equity / total assets |
| `INTEREST_EARNING_ASSETS` | carrying value of open securities and loans |

## Capital

| Column | Definition |
|---|---|
| `CET1_CAPITAL` | total equity − intangible assets − accumulated OCI (only when the AOCI filter is on) |
| `TIER1_CAPITAL` | CET1 + additional Tier 1 (input) |
| `TOTAL_CAPITAL` | Tier 1 + Tier 2 (input) |
| `CREDIT_RWA` | standardised credit risk-weighted assets: exposures (carrying value plus accrued interest) × CRE20 risk weights; other assets 100%, cash 0% |
| `OPERATIONAL_RWA` | operational-risk RWA (input, or estimated for Call Report banks) |
| `TOTAL_RWA` | credit + operational RWA |
| `CET1_RATIO`, `TIER1_RATIO`, `TOTAL_CAPITAL_RATIO` | capital / total RWA |
| `LEVERAGE_RATIO` | Tier 1 / (total assets − intangible assets) |

## Profitability

Over the trailing year (or since the start, when shorter), annualised; empty for the first 30 days.

| Column | Definition |
|---|---|
| `NET_INTEREST_MARGIN` | (interest income − interest expense) / average interest-earning assets |
| `ROA` | net income / average total assets |
| `ROE` | net income / average total equity |

## Interest-rate risk in the banking book

| Column | Definition |
|---|---|
| `EVE` | economic value of equity: present value of banking-book securities and loans on the day's curve (each with its credit spread), plus cash, less the present value of core deposits' run-off, less the other deposits and interest payable at book value |
| `DELTA_EVE_WORST` | the most negative change in EVE across the six Basel shocks, revaluing every cash flow on the shocked curve (MBS re-project their prepayments) |
| `DELTA_EVE_WORST_TO_TIER1` | `DELTA_EVE_WORST` / Tier 1; supervisors flag below −15% |
| `ASSET_DURATION` | effective duration of the securities and loans: the change in their value for a ±1bp parallel shift, per unit of value, in years |
| `NII_SENSITIVITY_UP`, `NII_SENSITIVITY_DOWN` | change in the next 12 months' net interest income for a +200bp / −200bp parallel shift, from the repricing gap: each item reprices at its next reset or maturity, weighted by the time left in the year |

In EVE, the core part of each deposit is the discounted run-off of its core balance; the rest
reprices overnight. In NII sensitivity, deposits reprice by their beta (see
[assumptions](../guides/assumptions.md#deposits)).

## Positions

`RunResult.carrying_value`, `.fair_value` and `.amortized_cost` hold one column per position:

| Value | Meaning |
|---|---|
| carrying value | what the account holds: amortised cost (HTM, loans) or fair value (AFS, trading) |
| amortised cost | cost rolled forward at the effective interest rate (bonds) or less principal repaid (loans, MBS); not kept for trading positions |
| fair value | clean present value of the remaining cash flows on the day's curve plus the position's spread; market days only |

Unrealised gain or loss = fair value − amortised cost.
