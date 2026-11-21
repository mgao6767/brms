# Scenarios

A scenario is the path of interest rates the bank lives through: the US Treasury curve (constant
maturity yields, from 1 month to 30 years) and the Prime rate, for every business day from the
start date to the end of the horizon. Everything before the start date is real history, so curves
and floating-rate fixings up to the start are the actual ones.

## Historical rates

The rates that actually happened, from the data shipped with the package (US Treasury yields and
the Prime rate, daily from 1990 to the end of 2025). The horizon cannot go past the end of the data:
the app tells you the longest horizon available for a bank.

## The six Basel shocks

| Shock | Shift at maturity *t* years (basis points) |
|---|---|
| Parallel up | +200 |
| Parallel down | −200 |
| Short rates up | +300 × e<sup>−t/4</sup> |
| Short rates down | −300 × e<sup>−t/4</sup> |
| Steepener | −0.65 × 300 e<sup>−t/4</sup> + 0.9 × 150 (1 − e<sup>−t/4</sup>) |
| Flattener | +0.8 × 300 e<sup>−t/4</sup> − 0.6 × 150 (1 − e<sup>−t/4</sup>) |

These are the US-dollar shock sizes of the Basel standard on interest-rate risk in the banking
book (SRP31). At the short end the steepener moves rates by −195bp and the flattener by +240bp; at
the long end by +135bp and −90bp.

## Parallel and key-rate shifts

- **Parallel shift**: any number of basis points at every maturity (`parallel+150`,
  `parallel-50` on the command line).
- **Key-rate shift**: basis points at chosen maturities. Between them the shift is linear in
  maturity; beyond the first and last it is flat. In the browser app the maturities are 3M, 1Y,
  2Y, 5Y, 10Y and 30Y; in Python any `(years, bp)` points:

```python
from brms.lab import KeyRateShift, Shock
Shock(KeyRateShift(((0.25, 300), (2, 200), (10, 50), (30, 25))), label="bear flattener")
```

## How a shock is applied

- The shift is added to each Treasury yield by maturity (1M, 3M, 6M, 1Y, 2Y, … 30Y) on the start
  date, then the curve **stays at that level** for the rest of the horizon. A shock is a jump to a
  new, constant curve, not a path.
- **Phase-in** (`ramp_days`): the shift grows linearly from zero on the start date to its full size
  after that many days, then stays.
- **Prime** moves by the shock's shift at 3 months, so floating-rate loans reprice with short rates.
- **Floor** (Python: `Shock(..., floor=0.0)`): shocked yields below the floor are set to it. By
  default yields may go negative.
- The shift applies to par yields (the quoted yields), which is close to, but not exactly, a shift
  of zero rates.

## Which scenario to use

| Question | Scenario |
|---|---|
| What did actually happen to this bank? | Historical rates |
| Is the bank an IRRBB outlier? How does it compare with peers? | The six Basel shocks (**Run all Basel shocks**) |
| What if rates rise gradually over a year? | Parallel up with a 365-day phase-in |
| What if the curve inverts? | Key-rate shift: up at the short end, down at the long end |
| A supervisory or central-bank scenario | Key-rate shift with the scenario's curve move |
