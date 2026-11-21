# How the engine works

The lab is a daily accounting simulation. Each calendar day it values every position, generates
the day's transactions from them, posts those as double-entry journal entries, and computes the
day's metrics. Everything you see is read from the ledger and the valuations, never estimated on
the side.

## One day

1. **Market data.** On business days the Treasury curve is built from the scenario's yields
   (a smooth zero curve through the quoted par yields), and Prime fixings are updated.
2. **Valuation.** For every open position:
    - *accrued interest* since the last payment;
    - *amortised cost* (effective-interest method for bonds; principal outstanding for loans and
      pass-throughs);
    - *fair value* on market days: the position's remaining cash flows (projected, for floating
      loans and MBS) discounted on the curve plus its credit spread, less accrued interest;
    - *carrying value*: amortised cost or fair value, depending on the accounting basis.
3. **Transactions.** Rules turn valuations and contracts into transactions:
    - interest accruals and their settlement;
    - premium and discount amortisation;
    - mark-to-market of AFS and trading positions;
    - coupon and principal payments, maturities and scheduled sales;
    - deposit interest, run-off and withdrawals;
    - operating costs, fees, income tax and dividends.
4. **Posting.** Each transaction becomes journal entries in a chart of accounts organised under
   IFRS 9 categories (amortised cost, FVOCI, FVTPL). Every entry balances.
5. **Metrics.** On market days: capital, RWA, ratios, profitability and interest-rate risk.

The books reconcile every day. Each account holding positions equals the sum of its positions'
carrying values, and assets equal liabilities plus equity. The test suite checks this for every day
of every shipped bank.

## Starting a bank

A simulation file (`.zip`) holds the instruments, positions, the opening balances of every
account, and market data. Building one from a bank file:

1. creates each instrument from its terms;
2. books each position as bought at the close of the as-of date at its book value (plus accrued
   interest), and books deposits, other assets and liabilities, with equity as the balance;
3. solves each bond's effective interest rate from its amortised cost and calibrates its credit
   spread to its fair value;
4. closes the books, so the run's income statement starts from zero.

## Libraries

Bond and loan cash flows, curves and pricing use [QuantLib](https://www.quantlib.org). Results are
pandas data frames. Runs are deterministic: the same bank and scenario give the same numbers.

## Limits

- **Static balance sheet**: no new business; maturing assets become cash (or roll over, with
  reinvestment).
- **No credit risk dynamics**: no defaults, provisions or spread changes.
- **Simple deposit behaviour**: rates follow a constant beta, balances a constant run-off or
  scheduled withdrawals, and the core share in EVE is fixed (the Basel caps for Call Report banks).
- **No liquidity metrics** (LCR, NSFR), derivatives or hedge accounting.
- **US focus**: Treasury curve, Prime rate, US calendars; Basel standardised approaches.
- **Mortgage-backed securities** pay down at a fixed speed; only their value responds to rates.

See [Assumptions](../guides/assumptions.md) for the details that matter when reading results.
