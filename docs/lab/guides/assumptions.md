# Assumptions

What the lab does, and does not do, to a bank as time passes. Read this before drawing conclusions
from a run.

## The balance sheet is static

The lab holds the bank's book as it was on the as-of date. It does not grow, originate new loans,
take new deposits or buy securities. As time passes:

- loans amortise and mature; the cash comes back and stays as cash;
- bonds pay coupons and mature into cash, unless **reinvestment** is on, which rolls each maturing
  bond into a new par bond of the same term at the market rate;
- deposits stay unless you give them run-off or withdrawals.

Cash earns nothing. A bank with a lot of maturing assets therefore loses interest income over a
long horizon: set reinvestment on when you want a constant-size balance sheet.

## Securities

- **HTM** (`AMORTIZED_COST`): carried at amortised cost by the effective interest method. Fair
  value is computed every market day but never enters the books.
- **AFS** (`FVOCI`): carried at fair value; the gap to amortised cost sits in accumulated OCI
  (AOCI) in equity. Interest income is at the effective rate. Selling recycles the AOCI into
  profit.
- **Trading** (`FVTPL`): carried at fair value; every mark goes to profit.
- **Fair value** discounts each position's cash flows on the day's Treasury curve plus a constant
  credit spread, calibrated so that the position is worth its reported fair value on the as-of
  date. Spreads do not change in a run: the lab isolates interest-rate risk.
- **Mortgage-backed securities** prepay faster when mortgage rates fall below the pool's note rate.
  Fair value and EVE project prepayments at the speed today's rates imply. Realised paydowns use a
  constant speed fixed on the as-of date.

## Loans

Loans are held at amortised cost, on the books at par. Fixed-rate loans amortise on schedule;
floating-rate loans pay Prime plus a spread, resetting monthly. Loans get a fair value (for
unrealised gains and losses and EVE) from the same constant credit spread. Credit losses and
provisions are **not** modelled.

## Deposits

- **Rate.** Each deposit pays its rate on the as-of date plus `beta` times the change in the
  3-month Treasury yield since then, never below zero. Interest accrues daily and is paid on the
  first of each month.
- **Balance.** `runoff_rate` removes a share of the balance continuously over the year, and
  `withdrawals` remove a fraction on given dates. The cash leaves with them.
- **In EVE and NII sensitivity, deposits reprice overnight.** The lab has no behavioural model of
  core deposits. When it computes the economic value of equity and the 12-month NII sensitivity,
  deposits are worth their balance and reprice at once. Real banks treat much of their deposit base
  as long-lived, which offsets part of the loss in value of fixed-rate assets when rates rise. The
  lab's ΔEVE is therefore closer to the exposure of the assets alone. Use it to compare banks, and
  do not read it as the bank's own IRRBB disclosure.

## Profit, tax and dividends

- **Interest** (accruals, coupons, premium and discount amortisation), **marks** on trading
  positions and **realised gains and losses** on sales are computed position by position.
- **Non-interest expense and income** (`operating`) are annual amounts booked through cash at 1/365
  a day. Without them, the bank has no costs.
- **Income tax** is accrued so that the tax for the period is the rate times the period's pre-tax
  profit, never below zero. A loss after profits reverses tax already booked. No deferred tax asset
  is recognised for losses beyond that.
- **Dividends** pay out the payout ratio times the period's profit after tax. Dividends paid are
  never taken back after a later loss.

## Capital

- **CET1** = total equity − intangible assets − (AOCI, when the AOCI filter is on).
- **Tier 1** = CET1 + additional Tier 1 (an input); **total capital** = Tier 1 + Tier 2 (an input).
- **Credit RWA** uses the Basel standardised approach (CRE20): each security and loan is weighted
  by its issuer type and rating (sovereign, public-sector entity, bank, corporate), mortgages by
  loan-to-value, retail loans at 75%. Cash is 0%; other assets 100%; intangibles are deducted.
- **Operational RWA** is an input; for Call Report banks the lab estimates it with the Basel
  standardised approach ([details](../reference/call-report.md#capital)).
- **Market-risk RWA** is not modelled: trading positions are weighted as credit exposures.
- **The leverage ratio** is Tier 1 over total assets less intangibles (on-balance-sheet exposure).

## Not modelled

Credit losses and provisions; liquidity ratios (LCR, NSFR); hedges and derivatives; changes in
credit spreads; deposit and loan growth; management actions. A negative cash balance is the lab's
signal that the bank needs funding. The lab does not borrow on the bank's behalf.
