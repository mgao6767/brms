---
hide:
  - navigation
  - toc
---

# Bank Risk Management Simulation

Put a bank's balance sheet through rising or falling interest rates and watch, day by day, what
happens to its books, its regulatory capital and its unrealised losses. Use any US bank, from its
public Call Report, or a bank you describe yourself.

The **Stress Lab** runs on your own computer and opens in your web browser. It is developed by
Dr. [Mingze Gao](https://mingze-gao.com) at [Macquarie Business School](https://www.mq.edu.au/macquarie-business-school)
for teaching and research.

![Silicon Valley Bank through 2022](images/lab/run.jpg)

## Get started in three steps

1. **Install it.** Follow [Install on your computer](lab/install.md): two commands, for Windows,
   macOS or Linux.
2. **Start it.** Run `brms` in a terminal. The lab opens in your browser.
3. **Try it.** The [quick start](lab/quickstart.md) walks you through your first run in five
   minutes.

## Learn from real banks

<div class="grid cards" markdown>

-   :material-bank-outline: **[Why SVB failed](lab/tutorials/svb-2022.md)**

    ---

    Run Silicon Valley Bank through the rates of 2022 and see $15bn of losses build up while its
    capital ratio still looked healthy.

-   :material-chart-bell-curve-cumulative: **[The Basel shocks](lab/tutorials/basel-shocks.md)**

    ---

    Apply the six standard rate shocks to SVB, Signature, First Republic and JPMorgan, and compare
    which bank is most exposed.

-   :material-run-fast: **[SVB's last week](lab/tutorials/svb-last-week.md)**

    ---

    Add a deposit run and a forced sale of securities, and see what the bank would have realised.

-   :material-file-document-outline: **[Any US bank](lab/tutorials/call-report.md)**

    ---

    Import a bank from its Call Report by its FDIC number and put it through any scenario.

</div>

## Look things up

<div class="grid cards" markdown>

-   :material-book-open-variant: **[Glossary](glossary.md)**

    ---

    AFS, HTM, AOCI, CET1, EVE and the other terms, in plain words.

-   :material-chart-line: **[Reading a run](lab/guides/reading-results.md)**

    ---

    What each chart and table in a run shows, and how to read them.

-   :material-tune-variant: **[Scenarios](lab/guides/scenarios.md) and [assumptions](lab/guides/assumptions.md)**

    ---

    The rate paths you can choose, and what the lab assumes about the bank.

-   :material-scale-balance: **[Basel III](basel_3/index.md)**

    ---

    The capital and liquidity rules behind the numbers.

</div>

Prefer code? The lab is also a Python library: see
[Python and the command line](lab/tutorials/python.md).
