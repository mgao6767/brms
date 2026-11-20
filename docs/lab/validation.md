# Validation: Silicon Valley Bank, 2022

Does the lab reproduce the unrealised losses a real bank reported? We take Silicon Valley Bank's
balance sheet at the end of 2021, run it through the actual Treasury yields of 2022, and compare
its unrealised losses at the end of 2022, as a share of amortised cost, with what SVB reported.
Rates of loss, not amounts, are compared, because SVB bought, sold and was repaid securities during
2022 while the lab holds the end-2021 book.

## From the Call Report alone

The [case study](tutorials/svb-2022.md) bank, built from SVB's Call Report with no other input.
The comparison is with the bank's end-2022 Call Report.

| Case | HTM, lab | HTM, reported | AFS, lab | AFS, reported |
|---|---:|---:|---:|---:|
| Call Report only | −14.0% | −16.6% | −13.6% | −8.9% |
| With the 10-K's AFS mix | −14.1% | −16.6% | −13.2% | −8.9% |

- **HTM** is within 2.6 percentage points.
- **AFS losses are overstated.** The filing does not say which securities are AFS. With the
  proportional split, the AFS book takes the bank's overall maturity profile, including long
  municipal bonds and 25-year MBS pools, while SVB's AFS Treasuries were mostly 1–5 years. Giving
  the class mix alone does not fix this: the maturity, not the class, is missing. SVB also turned
  over a third of its AFS book in 2022, which no static book reproduces.

Reproduce: `python -m brms.lab.examples.svb_call_report`.

## From the 10-K

A hand-built bank from SVB Financial Group's 10-K (USD millions): each securities book is one
instrument sized to the portfolio duration SVB reported.

| Case | HTM, lab | HTM, reported | AFS, lab | AFS, reported |
|---|---:|---:|---:|---:|
| Bullet bonds, durations as at end-2021 (HTM 4.1, AFS 3.5 years) | −9.7% | −16.6% | −8.1% | −8.9% |
| Bullet bonds, durations as at end-2022 (HTM 6.2, AFS 3.6 years) | −13.3% | −16.6% | −8.3% | −8.9% |
| HTM as an agency MBS pool (1.64% coupon, 25 years remaining) | −16.7% | −16.6% | −8.1% | −8.9% |

- **AFS** (mostly Treasuries) is reproduced to within one percentage point when its duration is
  right.
- **HTM as a bullet bond** is understated: a bullet bond cannot lengthen as SVB's MBS did (from 4.1
  to 6.2 years) when prepayments slowed.
- **HTM as an MBS pool** lands on the reported rate. Most of the improvement comes from treating
  the book as a long amortising pool. The pool's projected prepayment speed falls from 9.5% to 6.2%
  a year and its duration rises from 6.6 to 6.8 years. The remaining term is an assumption: 20
  years gives −15.1%, 28 years −17.5%.

Reproduce: `python -m brms.lab.examples.svb`.

## What this tells you

- The lab's valuation of fixed-rate securities through a real rate path is accurate when it is
  given the right maturity profile.
- From a Call Report alone, total unrealised losses are close and HTM is within a few points.
  The HTM/AFS split by maturity is the main uncertainty. Use the 10-K, or the FR Y-9C, when you need
  the AFS figure precisely.
- Both checks are part of the test suite (`tests/lab/test_svb.py`, `tests/lab/test_svb_call_report.py`).
