# Glossary

The terms used across these pages, in plain words. Throughout the site, abbreviations with a dotted
underline show their meaning when you hover over them.

## The balance sheet and accounting

Amortised cost
:   What a security or loan is carried at when it is not marked to market: the price paid, moved
    gradually towards the amount repaid at maturity. Changes in market rates do not change it.

Fair value
:   What a security would sell for today. When rates rise, the fair value of a fixed-rate bond
    falls.

Unrealised gain or loss
:   Fair value less amortised cost: what the bank would gain or lose if it sold the security today.
    It becomes *realised* only when the security is sold.

Held to maturity (HTM)
:   Securities the bank intends to keep until they mature. Carried at amortised cost, so their
    unrealised losses do not appear in the accounts or in capital. Most of SVB's losses were here.

Available for sale (AFS)
:   Securities the bank may sell. Carried at fair value; unrealised gains and losses go to equity,
    in AOCI, rather than to profit.

Accumulated other comprehensive income (AOCI)
:   The part of equity that holds unrealised gains and losses on AFS securities.

FVOCI and FVTPL
:   The IFRS 9 names for how a security is measured: at fair value through other comprehensive
    income (like AFS), or at fair value through profit or loss (a trading book).

Net interest income (NII)
:   Interest earned on assets less interest paid on deposits and borrowing: a bank's main source of
    profit.

## Capital

Regulatory capital
:   The equity a bank must hold to absorb losses, measured as regulators define it.

Common Equity Tier 1 (CET1)
:   The highest-quality capital: common equity less intangible assets such as goodwill. Under the US
    "AOCI filter", which smaller US banks could opt into, unrealised losses on AFS securities are
    left out of CET1; under Basel III they count.

Tier 1 and total capital
:   Tier 1 adds Additional Tier 1 (AT1) instruments, such as preferred stock, to CET1. Total
    capital adds Tier 2 capital, such as subordinated debt.

Risk-weighted assets (RWA)
:   The bank's exposures, each weighted by its riskiness: a Treasury bond weighs 0%, a corporate
    loan around 100%. The lab uses the Basel III standardised approach.

Capital ratio
:   Capital divided by RWA. The CET1 ratio must stay above 4.5%, plus buffers.

Leverage ratio
:   Tier 1 capital divided by total exposure, with no risk weights.

## Interest-rate risk

Basis point (bp)
:   One hundredth of a percentage point: +200bp means rates rise by 2 percentage points.

Yield curve
:   The interest rate for each maturity, from one month to thirty years. The lab uses US Treasury
    constant maturity (CMT) yields.

Interest rate risk in the banking book (IRRBB)
:   The risk that rate changes reduce a bank's value or income from the loans, securities and
    deposits it holds, rather than from trading.

Economic value of equity (EVE)
:   The present value of the bank's assets less that of its liabilities. ΔEVE is how much it changes
    under a rate shock.

The six Basel shocks
:   Standard rate scenarios from the Basel IRRBB standard: parallel up and down, steepener,
    flattener, and short rates up and down. See [Scenarios](lab/guides/scenarios.md).

Duration
:   How much a position's value changes when rates move: a duration of 5 years means it loses about
    5% for each 1 percentage point rise in rates.

Deposit beta
:   The share of a rise in market rates that a bank passes on to depositors. A beta of 0.35 means a
    +100bp rise lifts the deposit rate by 35bp.

Core deposits
:   The stable part of a bank's non-maturity deposits, which in practice stays for years even though
    customers could withdraw it at any time.

## Data and the lab

Call Report
:   The quarterly financial report every US bank files with its regulators, published by the FDIC.
    The lab can build a bank from one. See [Call Report mapping](lab/reference/call-report.md).

Bank file
:   A JSON file listing a bank's positions on a date, from which the lab builds a bank. See
    [Bank file](lab/reference/bank-file.md).

Scenario
:   The path of interest rates a run follows: actual historical rates or a shock. See
    [Scenarios](lab/guides/scenarios.md).

Run
:   One bank through one scenario, day by day, with its statements, capital and risk recorded for
    each day.
