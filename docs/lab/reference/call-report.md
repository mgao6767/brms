# Call Report mapping

How `brms.lab.call_report` turns a bank's Call Report into a [bank file](bank-file.md). Items come
from the FDIC BankFind financial data (FDIC field names in `code`), in USD thousands, as filed.
Income items are year-to-date and are annualised (×4 for March, ×2 for June, ×4/3 for September).

## Date

The bank is described as of the report date, or the Friday before when the quarter ends on a
weekend (the last business day). The official report date is kept in `source.report_date`.

## Assets

| Call Report | Becomes |
|---|---|
| Cash and due from banks `CHBAL` + fed funds sold and reverse repos `FREPO` | `cash` |
| Non-mortgage debt securities by remaining maturity or repricing (RC-B Memo 2: `SCNM3LES`, `SCNM3T12`, `SCNM1T3`, `SCNM3T5`, `SCNM5T15`, `SCNMOV15`) | fixed-rate bullet bonds maturing at the bucket midpoint (1.5 months, 7.5 months, 2, 4, 10 and 20 years), split into Treasuries (share `SCUST`, sovereign AA+) and other issuers (agencies and municipalities, PSE AA+) |
| Mortgage pass-throughs by remaining maturity (`SCPT…`) | agency MBS pools with that remaining term (2 months, 8 months, 2, 4, 10 and 25 years) |
| Other mortgage-backed securities by expected average life (`SCO3YLES`, `SCOOV3Y`) | bullet bonds at 2 and 6 years |
| Loans repricing or maturing within 3 months (`LNRS3LES`, `LNOT3LES`) | Prime floaters: monthly reset, 3-year bullet, spread = loan yield − Prime |
| Other 1–4 family loans by remaining maturity (`LNRS…`) | residential mortgages at the bucket midpoint, `ltv` as given (default 0.8) |
| Other loans by remaining maturity (`LNOT…`) | amortising fixed-rate loans at the bucket midpoint, corporate unrated |
| Intangible assets `INTAN` | `intangible_assets` (deducted from CET1) |
| Total assets `ASSET` less everything above | `other_assets` (risk-weighted 100%) |

Loans are scaled so that they sum to net loans `LNLSNET`.

**Securities yield and book.** Every security pays the bank's securities yield: securities income
`ISC` (annualised) over the five-quarter average of securities `SC5`. Loans pay the loan yield:
loan income `ILNLS` over average loans `LNLSGR5`.

The Memorandum 2 buckets combine HTM at amortised cost and AFS at fair value. Each class is split
between HTM and AFS in the bank's overall proportion (`SCHA` : `SCAF`), unless an AFS mix is given
(`afs=` in Python: fair value by class `treasury`, `other_debt`, `pass_through`, `other_mbs`). HTM
pieces get fair value in the ratio `SCHF / SCHA`; AFS pieces get amortised cost in the ratio
`SCAA / SCAF`. So the HTM and AFS totals and their fair values match the filing.

## Funding

| Call Report | Becomes |
|---|---|
| Noninterest-bearing deposits `DEPNIDOM` | a deposit at 0% |
| Interest-bearing deposits `DEP − DEPNIDOM` | a deposit at the bank's deposit cost (`EDEP` annualised over the balance), passing through `deposit_beta` (default 0.35) of moves in the 3-month yield |
| Other borrowed money `OTHBRF` + fed funds purchased and repos `FREPP` + subordinated notes `SUBND` | one floating-rate liability (`beta` 1) at its cost, `(EINTEXP − EDEP)` annualised over the balance |
| Total liabilities `LIAB` less the above | `other_liabilities` |

**Core deposits.** With `core_deposits` on (the default), each deposit line gets a `core_share` and
`core_maturity` from the Basel SRP31 caps, weighted by the uninsured share of domestic deposits
`DEPUNINS / DEPDOM` (all uninsured when the filing does not give it). Insured deposits count as
retail: 90% core with a 5-year average life for noninterest-bearing (transactional) deposits, 70%
and 4.5 years for interest-bearing. Uninsured deposits count as wholesale: 50% and 4 years.
Borrowings get no core share.

## Income

| Call Report | Becomes |
|---|---|
| Total noninterest expense `NONIX` | `operating.noninterest_expense` |
| Total noninterest income `NONII` | `operating.noninterest_income` |
| Applicable income taxes `ITAX` / income before taxes `IBEFTAX` | `operating.tax_rate` (21% if pre-tax income is not positive or the rate is outside 0–50%) |
| Cash dividends `EQCDIV` / net income `NETINC` | `operating.dividend_payout`, capped at 100% (0 without a profit) |

Credit-loss provisions are not used: the lab does not model credit losses.

## Capital

- `regulatory.aoci_filter`: an input (default on).
- `regulatory.preferred_equity`: perpetual preferred stock `EQPP` (Additional Tier 1, part of equity).
- `regulatory.tier2`: Tier 2 capital as reported, `RBCT2`.
- `regulatory.operational_rwa`: estimated with the Basel III standardised approach for
  operational risk. The business indicator is the smaller of |net interest income| and 2.25% of
  earning assets (`ERNAST`), plus non-interest income. It is multiplied by 12% up to $1bn, 15% from
  $1bn to $30bn and 18% above, with the internal loss multiplier at 1. RWA is 12.5 times the result.

## Kept for comparison

`reported` holds the filing's total assets `ASSET`, equity `EQ`, CET1 capital `RBCT1C`, CET1 ratio
`RBCT1CER`, RWA `RWAJ`, HTM and AFS amortised cost and fair value, intangibles and trading assets.
Equity in the lab should be within about 1% of `EQ`.

## Limits

- The filing does not say which securities are HTM and which AFS, or their maturities by book.
  With the proportional split, AFS takes the bank's overall maturity profile, which overstates AFS
  losses for banks whose AFS books are short (see [Validation](../validation.md)).
- Trading assets, equity securities and derivatives are in `other_assets`, at constant value.
- Deposits have no run-off; add it in the bank file.
