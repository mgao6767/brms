# Bank file reference

A bank file is a JSON object describing a bank's balance sheet on one date. Build it with
`python -m brms.lab build-bank bank.json --out bank.zip`, the browser app's **Import** page, or
`brms.lab.bank_file.build_bank`. A complete example: [`riverside.json`](../examples/riverside.json).

## Top level

| Key | Required | Meaning |
|---|---|---|
| `name` | no | the bank's name |
| `as_of` | **yes** | balance-sheet date, `YYYY-MM-DD` (a business day); the simulation starts the next day |
| `cash` | **yes** | cash and balances at banks |
| `deposits` | no | list of [deposits](#deposits) (and other funding) |
| `positions` | no | list of [positions](#positions): securities and loans |
| `other_assets` | no | assets not modelled one by one (premises, other); carried unchanged, risk-weighted 100% |
| `intangible_assets` | no | goodwill and other intangibles; carried unchanged, deducted from CET1 |
| `other_liabilities` | no | liabilities not modelled one by one; carried unchanged |
| `operating` | no | [operating flows](#operating): costs, fees, tax, dividends |
| `regulatory` | no | [regulatory inputs](#regulatory) |
| `unit` | no | the currency amount one unit of the file stands for (1000 if amounts are in thousands); used by the browser app for display |
| `story`, `source`, `reported` | no | free text and metadata, shown by the browser app; ignored by the engine |

Equity is not given: it is `cash + positions + other and intangible assets − deposits − other
liabilities`. It must be positive.

## Deposits

| Key | Required | Meaning |
|---|---|---|
| `id` | **yes** | unique id; the position is `pos-<id>` |
| `name` | no | display name |
| `balance` | **yes** | balance on the as-of date |
| `interest_rate` | **yes** | annual rate on the as-of date (0.01 = 1%) |
| `beta` | no | share of each change in the reference yield passed on (default 0) |
| `reference_tenor` | no | the Treasury yield the rate follows (default `"3 Mo"`) |
| `runoff_rate` | no | continuous annual run-off (0.1 = 10% a year) |
| `withdrawals` | no | `[["YYYY-MM-DD", fraction], …]`: a fraction of the balance then outstanding leaves on that date |
| `core_share` | no | share of the balance that is stable for interest-rate risk (Basel SRP31); default 0 |
| `core_maturity` | with `core_share` | average life of the core balance in years (Basel caps: 5 retail transactional, 4.5 retail other, 4 wholesale) |

Use a deposit with `beta: 1.0` for floating-rate borrowings.

## Positions

Every position has these keys, plus the [instrument terms](#instrument-types) of its `type`:

| Key | Required | Meaning |
|---|---|---|
| `id` | **yes** | unique id; the position is `pos-<id>` |
| `type` | **yes** | instrument type (below) |
| `name` | no | display name (generated from the terms otherwise) |
| `issuer` | **yes**\* | `{"name": …, "issuer_type": …, "credit_rating": …}` |
| `credit_rating` | no | an issue rating, which takes precedence over the issuer's |
| `basis` | no | `AMORTIZED_COST` (default), `FVOCI` or `FVTPL` |
| `book` | no | `BANKING` (default) or `TRADING` |
| `amortized_cost` | for `AMORTIZED_COST`, `FVOCI` | clean amortised cost on the as-of date |
| `fair_value` | for `FVOCI`, `FVTPL` | clean fair value on the as-of date; optional at amortised cost |

\* Mortgages are weighted by `ltv` instead and need no issuer for the risk weight, but every
position should name one.

Values are **clean**: without accrued interest, which the lab computes from the terms. The
position is treated as bought at the close of the as-of date at its book value; its credit spread
is calibrated to `fair_value` (or to the book value when no fair value is given).

**`issuer_type`**: `SOVEREIGN`, `PSE` (public-sector entities: agencies, states, municipalities),
`MDB`, `BANK`, `CORPORATE`, `SME`, `SECURITIES_FIRM`, `FINANCIAL_INSTITUTION`, `INSURANCE_COMPANY`,
`INDIVIDUAL`.

**`credit_rating`**: `AAA`, `AA_PLUS`, `AA`, `AA_MINUS`, `A_PLUS`, `A`, `A_MINUS`, `BBB_PLUS`, `BBB`,
`BBB_MINUS`, `BB_PLUS`, `BB`, `BB_MINUS`, `B_PLUS`, `B`, `B_MINUS`, `CCC_PLUS`, `CCC`, `CCC_MINUS`,
`CC`, `C`, `D`, `UNRATED`.

## Instrument types

Dates are `YYYY-MM-DD`; periods are a number and a unit, `"30Y"`, `"6M"`, `"1M"`; rates are
decimals.

### Bonds: `fixed_rate_bond`, `treasury_note`, `treasury_bond`

| Key | Meaning |
|---|---|
| `face_value` | face (par) amount |
| `coupon_rate` | annual coupon rate |
| `issue_date`, `maturity_date` | dates |
| `frequency` | coupon frequency, `"6M"` (default, semi-annual) or `"1Y"`, `"3M"` |

### Loans: `amortizing_fixed_rate_loan`, `residential_mortgage`, `commercial_mortgage`

| Key | Meaning |
|---|---|
| `face_value` | principal |
| `interest_rate` | annual rate |
| `issue_date` | start of the loan (the as-of date for a loan described as of today) |
| `maturity` | term from `issue_date`, e.g. `"30Y"` |
| `frequency` | payment frequency (mortgages default monthly; other loans semi-annual: give `"1M"`) |
| `ltv` | loan-to-value at origination (mortgages; required for the risk weight) |

Level payments (principal plus interest) amortise the loan to zero at maturity. Loans must be on
the books at par: `amortized_cost` equal to the principal outstanding.

### `variable_rate_loan`

| Key | Meaning |
|---|---|
| `face_value`, `issue_date`, `maturity` | as above |
| `spread` | margin over Prime (0.015 = 1.5%) |
| `benchmark_family` | `"prime"` |
| `repricing_frequency`, `payment_frequency` | e.g. `"1M"` |
| `principal_repayment_mode` | `"bullet"` (all at maturity) or `"sinking"` (equal instalments) |
| `floor_rate`, `cap_rate` | optional floor and cap on the all-in rate |

### `mortgage_backed_security`

An agency mortgage pass-through.

| Key | Meaning |
|---|---|
| `face_value` | pool balance |
| `coupon_rate` | pass-through rate paid to holders |
| `issue_date` | the as-of date |
| `maturity` | remaining term, e.g. `"25Y"` |
| `wac` | the mortgages' note rate (default coupon + 0.5%) |
| `pricing_cpr` | the constant annual prepayment rate for realised paydowns (default: the model's rate on the as-of date) |
| `prepayment` | the prepayment model (all optional): `turnover_cpr` (0.06), `max_cpr` (0.50), `refi_center` (0.0075), `refi_width` (0.0075), `mortgage_spread` (0.017) |

The annual prepayment rate is an S-curve in the refinancing incentive, `wac − mortgage rate`,
where the mortgage rate is the 10-year Treasury zero rate plus `mortgage_spread`. It rises from
`turnover_cpr` towards `max_cpr`, reaching the midpoint at an incentive of `refi_center`. Pools must
be on the books at par and held at `AMORTIZED_COST` or `FVOCI`.

## Operating

All optional; annual amounts in the file's unit.

| Key | Meaning |
|---|---|
| `noninterest_expense` | salaries, premises, technology and other costs per year |
| `noninterest_income` | fees and other non-interest income per year |
| `tax_rate` | income tax as a share of pre-tax profit (0.21 = 21%) |
| `dividend_payout` | share of profit after tax paid as dividends (0.3 = 30%) |

## Regulatory

| Key | Meaning |
|---|---|
| `aoci_filter` | `true` to exclude accumulated OCI from CET1 (US option for banks below the largest size) |
| `operational_rwa` | operational-risk RWA, added to credit RWA |
| `additional_tier1` | Additional Tier 1 capital instruments |
| `tier2` | Tier 2 capital |

## Building

The builder checks the file and stops with a message that names the position at fault. See
[Tutorial: build a bank from scratch](../tutorials/bank-file.md#when-something-is-wrong) for the
common messages.
