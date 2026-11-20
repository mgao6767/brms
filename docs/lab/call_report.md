# Any US bank from its Call Report

Every US insured bank files a Call Report each quarter. The FDIC publishes it through the free
BankFind API. One command turns a filing into a bank file:

```bash
python -m brms.lab call-report --cert 24735 --date 2021-12-31 --out svb.json
python -m brms.lab build-bank svb.json --out svb.zip
python -m brms.lab run svb.zip --scenario historical --scenario parallel+200 --months 12
```

`--cert` is the bank's FDIC certificate number (BankFind shows it). `--date` must be a quarter end.
Values stay in USD thousands, as reported.

From Python:

```python
from brms.lab.call_report import fetch_call_report, bank_file_from_call_report

items = fetch_call_report(24735, "2021-12-31")
bank = bank_file_from_call_report(items, prime=0.0325)
```

## What the bank file contains

| Call Report | Becomes |
|---|---|
| Cash and balances due, fed funds sold | cash |
| Non-mortgage debt securities by remaining maturity (6 buckets) | bullet bonds at each bucket's midpoint, Treasuries (sovereign) and other issuers (agency, municipal: PSE) |
| Mortgage pass-throughs by remaining maturity | agency MBS pools with that remaining term (over 15 years: 25 years) |
| Other MBS (CMOs, CMBS) by expected average life | bullet bonds at 2 and 6 years |
| Loans repricing within 3 months | Prime floaters |
| Other loans by remaining maturity | amortising fixed-rate loans; 1-4 family loans as residential mortgages (LTV 0.8 by default, `--ltv`) |
| Noninterest-bearing deposits | deposits at 0% |
| Interest-bearing deposits | deposits at the bank's deposit cost |
| Other borrowings, fed funds purchased, subordinated debt | one floating-rate liability |

- **Rates:** securities carry the bank's securities yield and loans its loan yield. Both are
  annualised year-to-date income over the five-quarter average balance.
- **Values:** the HTM and AFS totals and their fair values match the filing. Each position's
  credit spread is calibrated so that its value matches the reported one.
- **Equity** is the balancing figure. The reported equity, CET1 capital and ratio, and RWA are kept
  under `"reported"` for comparison.
- **Left out:** trading assets, premises, intangibles, and other assets and liabilities. They
  explain the gap between the plug and reported equity.

## Choices to review

- **HTM or AFS.** The FDIC data does not say which securities sit in which book, so every class
  splits in the bank's overall HTM : AFS proportion. If you know the AFS mix (from the 10-K or
  FR Y-9C), pass it with `afs={"treasury": ..., "other_debt": ..., "pass_through": ...,
  "other_mbs": ...}`. The mix is scaled to the reported AFS total. Maturities within a class still
  follow the bank's overall profile.
- **Deposit behaviour.** `beta` and `runoff_rate` are 0. Set them in the bank file.
- **Operational RWA** is not estimated, so ratios use credit RWA only.

## Check: SVB from its own Call Report

SVB (the bank, certificate 24735) at 31 Dec 2021 was run through actual 2022 yields. Unrealised
losses as a share of amortised cost at 31 Dec 2022:

| Case | HTM engine | HTM reported | AFS engine | AFS reported |
|---|---:|---:|---:|---:|
| Call Report only | −14.0% | −16.6% | −13.6% | −8.9% |
| With the 10-K AFS mix | −14.1% | −16.6% | −13.2% | −8.9% |

- **HTM** comes within 2.6 points with no input but the filing.
- **AFS** loses too much. It gets the bank's overall maturity profile, long municipal bonds and
  25-year pools included, while SVB's AFS Treasuries were mostly 1–5 years. Giving the class mix
  alone does not fix this, because it is the maturity, not the class, that is missing.
- **2022 trading:** SVB also turned over a third of its AFS book in 2022, which no static book
  reproduces.

The hand-built [SVB case](svb.md) uses the 10-K's durations and matches AFS. Run
`python -m brms.lab.examples.svb_call_report` to reproduce this table. `tests/lab/test_svb_call_report.py`
pins it.
