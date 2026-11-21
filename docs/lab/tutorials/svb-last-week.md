# Tutorial: SVB's last week, in Python

**Time:** 20 minutes · **You need:** Python 3.11+ and `pip install brms` · **You will learn:** how to
script the lab, add a deposit run, sell securities on a chosen day, and read the books from pandas.

## The story

On Wednesday 8 March 2023 SVB announced it had sold $21bn of AFS securities at a $1.8bn loss and
needed to raise capital. On Thursday 9 March depositors withdrew $42bn, about a quarter of all
deposits. On Friday the bank was closed.

You will replay that week on SVB's end-2022 balance sheet, twice: once holding everything, once
selling the AFS book on 8 March.

## Step 1: the bank

The lab ships SVB's Call Report for 31 December 2022. Turn it into a *bank file*, the lab's
plain-JSON description of a balance sheet (see the [bank file reference](../reference/bank-file.md)):

```python
import datetime
import json
from pathlib import Path

from brms.data.create_case_studies import CALL_REPORTS
from brms.lab import Historical, run
from brms.lab.bank_file import build_bank, default_market_frames, prime_on
from brms.lab.call_report import bank_file_from_call_report

items = json.loads((CALL_REPORTS / "svb_2022.json").read_text())
frames = default_market_frames()          # Treasury yields and the Prime rate, shipped with the package
bank = bank_file_from_call_report(items, prime=prime_on(frames, datetime.date(2022, 12, 31)))
```

`bank` is now a plain dictionary: `bank["deposits"]`, `bank["positions"]`, `bank["operating"]`
and so on. Print `bank["deposits"]` to see the three funding lines: noninterest-bearing deposits
(`nib`), interest-bearing deposits (`ib`) and other borrowings.

!!! tip "Any bank"
    Replace the first line with `items = fetch_call_report(24735, "2022-12-31")` (from
    `brms.lab.call_report`) to fetch any bank's filing from the FDIC.

## Step 2: the run on deposits

A deposit can carry scheduled withdrawals: `[date, fraction of the balance then outstanding]`.
Take a quarter of both deposit lines on 9 March:

```python
for deposit in bank["deposits"]:
    if deposit["id"] in {"nib", "ib"}:
        deposit["withdrawals"] = [["2023-03-09", 0.25]]
```

Build the simulation. This values every position on the as-of date and writes a self-contained zip:

```python
Path("svb_run.json").write_text(json.dumps(bank, indent=1))
simulation = build_bank(Path("svb_run.json"), frames, Path("svb_run.zip"))
```

## Step 3: two runs

`run` takes the simulation, a scenario and options; `sales` maps position ids to the day each
position is sold at fair value. AFS positions are those with basis `FVOCI`:

```python
afs = [f"pos-{p['id']}" for p in bank["positions"] if p["basis"] == "FVOCI"]
end = datetime.date(2023, 3, 10)
hold = run(simulation, Historical(), end=end)
sell = run(simulation, Historical(), end=end, sales=dict.fromkeys(afs, datetime.date(2023, 3, 8)))
```

Each run takes a few seconds and returns a `RunResult`.

## Step 4: read the books

`RunResult.statements` holds the balance sheet and income statement for every market day, one row
per line (`date`, `section`, `account`, `balance`). A small helper reads one line, in billions:

```python
def line(result, day, account):
    s = result.statements
    row = s[(s["date"] == day) & (s["account"] == account)]
    return float(row["balance"].iloc[0]) / 1e6   # the Call Report is in USD thousands

for name, result in (("hold", hold), ("sell AFS", sell)):
    for day in (datetime.date(2023, 3, 7), datetime.date(2023, 3, 8), datetime.date(2023, 3, 9)):
        print(name, day,
              round(line(result, day, "Cash and Cash Equivalents"), 1),
              round(line(result, day, "Accumulated OCI"), 1),
              round(line(result, day, "net_income"), 1))
    cet1 = result.metrics["CET1_RATIO"].dropna()
    print(name, "CET1", f"{cet1.iloc[-1]:.1%}")
```

Output (USD billions):

| Run | Day | Cash | Accumulated OCI | Net income since 1 Jan |
|---|---|---:|---:|---:|
| hold | 7 Mar | 15.5 | −2.7 | 0.4 |
| hold | 9 Mar | **−28.4** | −2.6 | 0.4 |
| sell AFS | 8 Mar | 41.1 | 0.0 | **−2.2** |
| sell AFS | 9 Mar | **−2.7** | 0.0 | −2.2 |

CET1 ratio on 10 March: **17.7%** holding, **15.9%** after the sale.

## What happened

- **Selling turns an unrealised loss into a realised one.** Before the sale, the AFS loss sat in
  accumulated OCI (−$2.7bn), outside profit and, with the AOCI filter, outside CET1. Selling moves
  it into the income statement (*Investment Income (FVOCI)* −$2.7bn), and net income for the year
  turns negative. Total equity hardly moves: the loss was already in equity, in AOCI. The
  regulatory ratio falls, because realised losses do count in CET1. SVB itself reported a $1.8bn
  loss on the $21bn it sold.
- **The cash was not enough.** A quarter of deposits is $43.8bn. Holding everything, cash goes to
  −$28.4bn: a hole the bank must borrow to fill. Even after selling the whole AFS book, cash is
  −$2.7bn. The rest of the assets are loans and HTM securities, which carry losses of their own.
- **Negative cash is the lab's signal of a funding gap.** The lab does not borrow for you; it shows
  how much the bank would have had to raise.

## Look at it in the browser

Everything you built can be opened in the browser app: start `brms-web`, go to **Import**, paste
the contents of `svb_run.json` into **From a bank file**, and build. The withdrawal is part of the
bank, so any run of it includes the deposit run.

## Try next

- Make the run gradual instead: drop the withdrawals and give the deposits `"runoff_rate": 0.5`
  (half the balance leaves over a year, continuously).
- Sell only some AFS positions: the ids are listed in `bank["positions"]`.
- Plot `hold.metrics["CET1_RATIO"]` and `sell.metrics["CET1_RATIO"]` with pandas.
- See [Python and the command line](python.md) for everything a `RunResult` holds.
