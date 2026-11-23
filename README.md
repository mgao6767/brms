# BRMS - Bank Risk Management Simulation

![LICENSE](https://img.shields.io/github/license/mgao6767/brms?color=blue)

Put a bank's balance sheet through rising or falling interest rates and watch, day by day, what
happens to its books, its regulatory capital and its unrealised losses. Use any US bank, from its
public Call Report (SVB, Signature, First Republic and JPMorgan ship as case studies), or a bank you
describe yourself.

It is developed by Dr. [Mingze Gao](https://mingze-gao.com) from the Department of Applied Finance
at [Macquarie Business School](https://www.mq.edu.au/macquarie-business-school), for teaching
AFIN8003 Banking and Financial Intermediation and for research.

![Silicon Valley Bank through 2022](docs/images/lab/run.jpg)

## Get started

The Stress Lab runs on your own computer and opens in your browser at `http://127.0.0.1:8765`.

```bash
uv tool install "brms[web]>=0.2"   # or: python -m pip install "brms[web]>=0.2" (Python 3.11+)
brms-web                           # the lab in your browser
```

Step by step, for Windows, macOS and Linux: [Install on your computer](docs/lab/install.md).

Then follow the [quick start](docs/lab/quickstart.md) and the tutorials, starting with
[why SVB failed, step by step](docs/lab/tutorials/svb-2022.md). The full documentation is at
[bankrisk.org](https://bankrisk.org).
