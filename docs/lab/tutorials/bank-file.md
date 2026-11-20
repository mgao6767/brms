# Tutorial: build a bank from scratch

**Time:** 30 minutes · **You need:** a text editor, and the browser app or the command line ·
**You will learn:** how to describe a balance sheet in a *bank file*, build it and run it.

A bank file is a JSON document listing a bank's positions on one date (the *as-of* date), with
their contract terms and book values. The lab turns it into a simulation: every security and loan
is treated as bought on the as-of date at its book value, and equity is whatever balances the books.

We will build **Riverside Community Bank**, a $1.6bn bank with Treasuries, agency MBS, municipal
bonds, mortgages, business loans and consumer loans. The finished file is
[`riverside.json`](../examples/riverside.json).

## Step 1: the frame

```json
{
  "name": "Riverside Community Bank",
  "as_of": "2021-12-31",
  "cash": 60000000,
  "deposits": [],
  "positions": []
}
```

- `as_of` is the balance-sheet date. The simulation starts the next day. Pick a business day.
- Amounts are in currency units (here dollars). Use the same unit everywhere. If you work in
  thousands, add `"unit": 1000` so the browser app shows dollars.
- `cash` is cash and balances at other banks.

## Step 2: deposits

```json
"deposits": [
  {"id": "checking", "name": "Checking accounts", "balance": 680000000, "interest_rate": 0.0, "runoff_rate": 0.05},
  {"id": "savings", "name": "Savings and money market", "balance": 520000000, "interest_rate": 0.001, "beta": 0.3},
  {"id": "time", "name": "Time deposits", "balance": 230000000, "interest_rate": 0.008, "beta": 0.6}
]
```

| Field | Meaning |
|---|---|
| `balance` | balance on the as-of date |
| `interest_rate` | rate paid on the as-of date (0.001 = 0.1%) |
| `beta` | share of each move in the 3-month Treasury yield passed on (0.3 = 30%); the rate never goes below zero |
| `runoff_rate` | share of the balance that leaves per year, continuously (0.05 = 5% a year) |
| `withdrawals` | one-off outflows: `[["2023-03-09", 0.25]]` takes 25% of the balance on 9 March 2023 |

Interest is accrued daily and paid on the first of each month.

## Step 3: securities

Each position has an `id`, a `type`, its contract terms, an `issuer`, an accounting `basis` and
its book values:

```json
{"id": "ust", "type": "treasury_note", "face_value": 150000000, "coupon_rate": 0.0125,
 "issue_date": "2021-11-30", "maturity_date": "2026-11-30",
 "issuer": {"name": "US Treasury", "issuer_type": "SOVEREIGN", "credit_rating": "AA_PLUS"},
 "basis": "FVOCI", "amortized_cost": 149500000, "fair_value": 149000000}
```

- `basis` is the accounting category: `AMORTIZED_COST` (held to maturity), `FVOCI` (available for
  sale) or `FVTPL` (trading).
- `amortized_cost` and `fair_value` are **clean** values (without accrued interest). FVOCI needs
  both; AMORTIZED_COST needs `amortized_cost` (and `fair_value` if you have it); FVTPL needs
  `fair_value`.
- The lab solves each bond's effective interest rate from its amortised cost, and calibrates a
  credit spread so that its fair value on the as-of date is the one you gave.
- `issuer` drives the credit risk weight: `SOVEREIGN`, `PSE` (agencies, municipalities), `BANK`,
  `CORPORATE`, `INDIVIDUAL`… with a `credit_rating` such as `AA_PLUS`.

An agency mortgage pass-through and a municipal bond:

```json
{"id": "mbs", "type": "mortgage_backed_security", "face_value": 250000000, "coupon_rate": 0.02,
 "issue_date": "2021-12-31", "maturity": "28Y",
 "issuer": {"name": "Agency MBS", "issuer_type": "PSE", "credit_rating": "AA_PLUS"},
 "basis": "AMORTIZED_COST", "amortized_cost": 250000000, "fair_value": 248000000},
{"id": "muni", "type": "fixed_rate_bond", "face_value": 60000000, "coupon_rate": 0.025,
 "issue_date": "2020-06-01", "maturity_date": "2035-06-01",
 "issuer": {"name": "State and municipal", "issuer_type": "PSE", "credit_rating": "AA"},
 "basis": "AMORTIZED_COST", "amortized_cost": 61000000, "fair_value": 62000000}
```

The MBS pool's prepayments speed up when mortgage rates fall and slow when they rise; see the
[bank file reference](../reference/bank-file.md#mortgage-backed-security).

## Step 4: loans

Loans are held at amortised cost and must be on the books at par (amortised cost = face value
outstanding):

```json
{"id": "mortgages", "type": "residential_mortgage", "face_value": 500000000, "interest_rate": 0.031,
 "issue_date": "2021-12-31", "maturity": "30Y", "ltv": 0.7,
 "issuer": {"name": "Households", "issuer_type": "INDIVIDUAL"},
 "basis": "AMORTIZED_COST", "amortized_cost": 500000000},
{"id": "business", "type": "variable_rate_loan", "face_value": 400000000, "spread": 0.015,
 "issue_date": "2021-12-31", "maturity": "5Y", "benchmark_family": "prime",
 "repricing_frequency": "1M", "payment_frequency": "1M", "principal_repayment_mode": "bullet",
 "issuer": {"name": "Local businesses", "issuer_type": "CORPORATE"},
 "basis": "AMORTIZED_COST", "amortized_cost": 400000000},
{"id": "consumer", "type": "amortizing_fixed_rate_loan", "face_value": 120000000, "interest_rate": 0.045,
 "issue_date": "2021-12-31", "maturity": "5Y", "frequency": "1M",
 "issuer": {"name": "Consumers", "issuer_type": "INDIVIDUAL"},
 "basis": "AMORTIZED_COST", "amortized_cost": 120000000}
```

- A mortgage needs `ltv` (loan-to-value, 0.7 = 70%) for its risk weight.
- The business loan pays the Prime rate plus 1.5%, resetting monthly.
- Periods are written `"30Y"`, `"5Y"`, `"1M"`.

## Step 5: everything else

```json
"other_assets": 30000000,
"other_liabilities": 15000000,
"operating": {"noninterest_expense": 28000000, "noninterest_income": 6000000, "tax_rate": 0.21, "dividend_payout": 0.3},
"regulatory": {"aoci_filter": true, "operational_rwa": 60000000}
```

- `other_assets` (premises, goodwill, other) and `other_liabilities` are carried unchanged. Other
  assets are risk-weighted at 100%.
- `operating` gives the annual non-interest expense (salaries, premises, technology) and income
  (fees), the tax rate, and the share of profit after tax paid out as dividends. Without it, the
  bank has no costs and pays no tax.
- `regulatory`: whether AOCI is excluded from CET1, and the operational-risk RWA (the lab does not
  derive it from a bank file). `additional_tier1` and `tier2` can also be given.

## Step 6: build and run it

=== "Browser"

    1. Start `brms-web` and open **Import**.
    2. Drop `riverside.json` on **From a bank file** (or paste it), then click **Build from bank file**.
    3. On the bank's page, click **Run all Basel shocks**.

=== "Command line"

    ```bash
    python -m brms.lab build-bank riverside.json --out riverside.zip
    python -m brms.lab run riverside.zip --scenario historical --scenario parallel+200 \
        --scenario steepener --months 12 --out results
    ```

    `results/<scenario>/` then holds `metrics.csv` (every metric, every market day),
    `carrying_value.csv`, `fair_value.csv` and `summary.json`.

Output of the command line:

```
scenario            CET1 end  CET1 min   dEVE/T1     net income
historical            18.00%    15.88%  -134.15%     18,091,207
parallel_up           18.12%    15.88%  -101.36%     19,417,565
steepener             17.72%    15.88%  -113.47%     15,047,752
```

Riverside starts with a CET1 ratio of 15.9% and builds capital through the year. The large ΔEVE
numbers come from the lab treating deposits as repricing overnight in economic-value terms. See
[assumptions](../guides/assumptions.md#deposits).

## When something is wrong

The builder checks the file and stops with a message naming the position:

| Message | Fix |
|---|---|
| *Position 'x' (FVOCI) needs 'fair_value'* | Add the missing value. |
| *loans bought at a premium or discount are not supported yet* | Make the loan's `amortized_cost` equal its `face_value`. |
| *The bank file implies non-positive equity* | Assets must exceed deposits and other liabilities. |
| *cannot be risk-weighted: the mortgage has no loan-to-value ratio* | Add `ltv` to mortgages. |
| *Unknown prepayment model fields* / *Unknown operating fields* | Check the spelling against the [reference](../reference/bank-file.md). |
