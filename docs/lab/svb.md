# Case study: Silicon Valley Bank, 2022

SVB's balance sheet at 31 December 2021 (Form 10-K FY2021) is rebuilt as a bank file and run through
actual 2022 Treasury yields. The question: does the engine reproduce the unrealised losses on
securities that SVB reported at 31 December 2022 (Form 10-K FY2022)?

Run it yourself: `python -m brms.lab.examples.svb`.

## Inputs (USD millions, 31 Dec 2021)

| Item | Amount | Modelled as |
|---|---:|---|
| Cash | 14,586 | cash |
| HTM securities | 98,202 amortised cost, 97,227 fair value, yield 1.64% | one bullet bond, or one agency MBS pool (see below) |
| AFS securities | 27,370 amortised cost, 27,221 fair value, yield 1.17% | one bullet bond, sovereign issuer |
| Loans (net) | 65,854 | Prime-linked floating loan |
| Noninterest-bearing deposits | 125,851 | run-off to 80,753 by end-2022 |
| Interest-bearing deposits | 63,352 | rate 0.13%, beta 0.23 |
| Equity (balancing) | 16,660 | reported 16,609 |

Three variants:

1. **Bullet bonds, durations as at end-2021.** Each book is one bond whose maturity gives the
   modified duration SVB reported at the start of 2022 (HTM 4.1, AFS 3.5 years).
2. **Bullet bonds, durations as at end-2022.** The same with the durations reported at the end
   (HTM 6.2, AFS 3.6), after the extension that actually happened.
3. **HTM as an MBS pool.** The HTM book, mostly agency mortgage-backed securities, is one
   pass-through pool: coupon 1.64% (the book yield, so it is bought at par), mortgage note rate
   2.14%, 25 years remaining, the default prepayment model. AFS is as in variant 1.

## Results: unrealised loss as a share of amortised cost at 31 Dec 2022

| Case | HTM engine | HTM reported | AFS engine | AFS reported |
|---|---:|---:|---:|---:|
| Durations as at end-2021 | −9.7% | −16.6% | −8.1% | −8.9% |
| Durations as at end-2022 | −13.3% | −16.6% | −8.3% | −8.9% |
| HTM as an MBS pool | −16.7% | −16.6% | −8.1% | −8.9% |

## Reading the result

- **AFS** (mostly Treasuries) is reproduced to within one percentage point.
- **HTM as a bullet bond** is understated by 3–7 percentage points. A bullet bond cannot extend as
  SVB's MBS did (4.1 to 6.2 years). Also, agency MBS spreads widened in 2022 while the engine holds
  each position's spread constant.
- **HTM as an MBS pool** lands on the reported rate. The pool's projected speed falls from 9.5% to
  6.2% CPR a year, and its effective duration goes from 6.6 to 6.8 years. Most of the improvement
  comes from treating the book as a long amortising pool. The extension itself is small here,
  because a 1.64% pool was already far from refinancing at end-2021. Its starting duration is
  longer than the 4.1 years SVB reported, because SVB held premium pools prepaying faster than a
  par pool can. Read the match as "a plain agency pool with standard prepayment behaviour loses
  what SVB lost", not as a calibration. The remaining term is an assumption: 20 years gives
  −15.1%, 28 years −17.5%.
- Rates, not amounts, are compared: SVB sold, bought and was repaid on securities during 2022, and
  the engine holds the end-2021 book.
- The known reported loss of 15.2bn on HTM never reached regulatory capital (held at amortised cost)
  and the 2.5bn on AFS was excluded by the AOCI filter SVB was allowed to use. Running the case with
  `RegulatoryConfig(aoci_filter=False)` shows the CET1 ratio the market was implicitly looking at.

This case is pinned by `tests/lab/test_svb.py`.
