# Tutorial: SVB's last week

**Time:** 20 minutes · **You need:** the browser app, or Python 3.11+ with `pip install brms` ·
**You will learn:** how to add a deposit run and a sale of securities to a scenario, and how to
read a liquidity gap from the books.

## The story

On Wednesday 8 March 2023 SVB announced it had sold $21bn of available-for-sale (AFS) securities at
a $1.8bn loss and needed to raise capital. On Thursday 9 March depositors withdrew $42bn, about a
quarter of all deposits. On Friday the bank was closed.

You will replay that week on SVB's balance sheet at the end of 2022, twice: once holding
everything, once selling the AFS book on 8 March. Both times a quarter of deposits leaves on
9 March.

## In the browser

1. Open **Banks → Silicon Valley Bank, end-2022**.
2. In **Run a scenario**: **Historical rates**, horizon **3** months.
3. Open **Liquidity stress (optional)** and set:
    - **Withdrawal (% of deposits):** `25`, **on** `2023-03-09`.
4. **Label:** `Run, hold`. Click **Run scenario**.
5. Back on the bank, run it again with the same withdrawal and also **Sell all AFS securities on**
   `2023-03-08`. **Label:** `Run, sell AFS`.
6. In **Runs**, tick both and click **Compare 2 selected**. Then open each run, drag the **Books**
   slider to 7, 8 and 9 March 2023, and read **Cash and Cash Equivalents**, **Accumulated OCI** and
   **Net income** in **Statements**.

The withdrawal applies to deposits only; SVB's other borrowings stay.

## In Python

The same two runs, on the case study shipped with the package:

```python
import datetime

from brms.data import DEFAULT_DATA_FOLDER
from brms.lab import DepositStress, Historical, run

svb = DEFAULT_DATA_FOLDER.parent / "case_svb_2022.zip"
run_on_deposits = DepositStress(withdrawal=0.25, withdrawal_date=datetime.date(2023, 3, 9))
end = datetime.date(2023, 3, 10)

hold = run(svb, Historical(), end=end, deposit_stress=run_on_deposits)
sell = run(svb, Historical(), end=end, deposit_stress=run_on_deposits, sell_afs_on=datetime.date(2023, 3, 8))
```

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
    print(name, "CET1", f"{result.metrics['CET1_RATIO'].dropna().iloc[-1]:.1%}")
```

## The results

USD billions; net income is for 2023 so far:

| Run | Day | Cash | Accumulated OCI | Net income |
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
  −$2.7bn. The rest of the assets are loans and held-to-maturity securities, and the HTM securities
  were $14.1bn under water by then (`hold.summary["unrealised_end"]["htm"]`). Selling them would have
  realised that loss, almost all of the bank's equity.
- **Negative cash is the lab's signal of a funding gap.** The lab does not borrow for you; it shows
  how much the bank would have had to raise.

## Going further

- **A slow run instead of a sudden one.** Use **Deposit run-off (% a year)** (Python:
  `DepositStress(runoff_rate=0.5)`): the balance leaves continuously from the start date.
- **Different behaviour per deposit.** Liquidity stress applies to every deposit. To give each its
  own, write a bank file: each deposit takes `runoff_rate` and `withdrawals`
  (`[["2023-03-09", 0.25]]`). Mark borrowings with `"borrowing": true` so a deposit stress leaves
  them alone. See the [bank file reference](../reference/bank-file.md#deposits) and
  [a bank from its Call Report](call-report.md#from-python-or-the-command-line), which shows how
  to get SVB's bank file to edit.
- **On the command line:** `python -m brms.lab run svb.zip --scenario historical --months 3
  --withdrawal 0.25 --withdrawal-date 2023-03-09 --sell-afs-on 2023-03-08`.
