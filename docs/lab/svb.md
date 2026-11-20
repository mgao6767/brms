# Case study: Silicon Valley Bank, 2022

SVB's balance sheet at 31 December 2021 (Form 10-K FY2021) is rebuilt as a bank file and run through
actual 2022 Treasury yields. The question: does the engine reproduce the unrealised losses on
securities that SVB reported at 31 December 2022 (Form 10-K FY2022)?

Run it yourself: `python -m brms.lab.examples.svb`.

## Inputs (USD millions, 31 Dec 2021)

| Item | Amount | Modelled as |
|---|---:|---|
| Cash | 14,586 | cash |
| HTM securities | 98,202 amortised cost, 97,227 fair value, yield 1.64% | one bullet bond, agency issuer |
| AFS securities | 27,370 amortised cost, 27,221 fair value, yield 1.17% | one bullet bond, sovereign issuer |
| Loans (net) | 65,854 | Prime-linked floating loan |
| Noninterest-bearing deposits | 125,851 | run-off to 80,753 by end-2022 |
| Interest-bearing deposits | 63,352 | rate 0.13%, beta 0.23 |
| Equity (balancing) | 16,660 | reported 16,609 |

The bond maturities are chosen so that their modified duration equals SVB's reported portfolio
duration. Two variants: the durations reported at the start of 2022 (HTM 4.1, AFS 3.5 years) and at
the end (HTM 6.2, AFS 3.6 years).

## Results: unrealised loss as a share of amortised cost at 31 Dec 2022

| Case | HTM engine | HTM reported | AFS engine | AFS reported |
|---|---:|---:|---:|---:|
| Durations as at end-2021 | −9.7% | −16.6% | −8.1% | −8.9% |
| Durations as at end-2022 | −13.3% | −16.6% | −8.3% | −8.9% |

## Reading the result

- **AFS** (mostly Treasuries) is reproduced to within one percentage point.
- **HTM** is understated by 3–7 percentage points. Two reasons, both outside the engine's current
  scope: the HTM book was mostly agency mortgage-backed securities whose duration extended from 4.1
  to 6.2 years as prepayments slowed, which a bullet bond cannot do; and agency MBS spreads widened
  in 2022 while the engine holds each position's spread constant.
- Rates, not amounts, are compared: SVB sold, bought and was repaid on securities during 2022, and
  the engine holds the end-2021 book.
- The known reported loss of 15.2bn on HTM never reached regulatory capital (held at amortised cost)
  and the 2.5bn on AFS was excluded by the AOCI filter SVB was allowed to use. Running the case with
  `RegulatoryConfig(aoci_filter=False)` shows the CET1 ratio the market was implicitly looking at.

This case is pinned by `tests/lab/test_svb.py`.
