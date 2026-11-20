"""Command line: ``python -m brms.lab run <simulation.zip> --scenario parallel+200 --months 12 --out results``."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from brms.data import DEFAULT_DATA_FOLDER
from brms.lab.bank_file import build_bank
from brms.lab.runner import run_many
from brms.lab.scenarios import parse_scenario


def _write(result: object, out: Path) -> None:
    folder = out / result.name  # type: ignore[attr-defined]
    folder.mkdir(parents=True, exist_ok=True)
    result.metrics.to_csv(folder / "metrics.csv")  # type: ignore[attr-defined]
    result.carrying_value.to_csv(folder / "carrying_value.csv")  # type: ignore[attr-defined]
    result.fair_value.to_csv(folder / "fair_value.csv")  # type: ignore[attr-defined]
    (folder / "summary.json").write_text(json.dumps(result.summary, indent=2))  # type: ignore[attr-defined]


def main(argv: list[str] | None = None) -> int:
    """Run the CLI."""
    parser = argparse.ArgumentParser(prog="python -m brms.lab", description="Run a bank through rate scenarios.")
    commands = parser.add_subparsers(dest="command", required=True)
    run_cmd = commands.add_parser("run", help="run scenarios and write results")
    run_cmd.add_argument("simulation", type=Path, help="simulation zip")
    run_cmd.add_argument("--scenario", action="append", default=None,
                         help="historical, parallel+200, parallel-200, steepener, flattener, short+300, "
                              "short-300 or parallel+<bp>; repeatable")
    run_cmd.add_argument("--months", type=int, default=None, help="horizon in months from the start date")
    run_cmd.add_argument("--workers", type=int, default=None, help="worker processes")
    run_cmd.add_argument("--out", type=Path, default=Path("results"), help="output folder")
    build_cmd = commands.add_parser("build-bank", help="build a simulation zip from a point-in-time bank file")
    build_cmd.add_argument("bank_file", type=Path, help="bank.json")
    build_cmd.add_argument("--yields", type=Path, default=DEFAULT_DATA_FOLDER / "treasury_yields.csv",
                           help="Treasury CMT yields CSV (percent, date-indexed)")
    build_cmd.add_argument("--benchmarks", type=Path, default=DEFAULT_DATA_FOLDER / "prime_rates.csv",
                           help="Prime rate CSV (DPRIME), used for variable-rate loans")
    build_cmd.add_argument("--out", type=Path, required=True, help="simulation zip to write")
    report_cmd = commands.add_parser("call-report", help="write a bank file from a US bank's Call Report (FDIC)")
    report_cmd.add_argument("--cert", type=int, required=True, help="FDIC certificate number (e.g. 24735)")
    report_cmd.add_argument("--date", required=True, help="quarter-end report date, e.g. 2021-12-31")
    report_cmd.add_argument("--ltv", type=float, default=0.8, help="loan-to-value assumed for 1-4 family loans")
    report_cmd.add_argument("--no-aoci-filter", action="store_true", help="include AOCI in CET1")
    report_cmd.add_argument("--deposit-beta", type=float, default=0.35,
                            help="share of 3-month yield moves passed to interest-bearing deposits (default 0.35)")
    report_cmd.add_argument("--out", type=Path, required=True, help="bank.json to write")
    args = parser.parse_args(argv)

    if args.command == "call-report":
        import datetime

        from brms.lab import call_report
        from brms.lab.bank_file import default_market_frames, prime_on

        items = call_report.fetch_call_report(args.cert, args.date)
        prime = prime_on(default_market_frames(), datetime.date.fromisoformat(args.date))
        bank = call_report.bank_file_from_call_report(items, prime=prime, ltv=args.ltv,
                                                      aoci_filter=not args.no_aoci_filter,
                                                      deposit_beta=args.deposit_beta)
        args.out.write_text(json.dumps(bank, indent=2))
        sys.stdout.write(f"Wrote {args.out} ({bank['name']})\n")
        return 0

    if args.command == "build-bank":
        import pandas as pd

        frames = {"yields": pd.read_csv(args.yields, index_col="date", parse_dates=True)}
        if args.benchmarks and args.benchmarks.exists():
            frames["benchmarks"] = pd.read_csv(args.benchmarks, index_col="date", parse_dates=True)
        build_bank(args.bank_file, frames, args.out)
        sys.stdout.write(f"Created {args.out}\n")
        return 0

    scenarios = [parse_scenario(s) for s in (args.scenario or ["historical"])]
    results = run_many(args.simulation, scenarios, workers=args.workers, months=args.months)
    for result in results:
        _write(result, args.out)
    header = f"{'scenario':<18}{'CET1 end':>10}{'CET1 min':>10}{'dEVE/T1':>10}{'net income':>15}"
    sys.stdout.write(header + "\n")
    for result in results:
        s = result.summary

        def pct(value: float | None) -> str:
            return "-" if value is None else f"{value:.2%}"

        line = (f"{s['scenario']:<18}{pct(s['cet1_ratio_end']):>10}{pct(s['cet1_ratio_min']):>10}"
                f"{pct(s['worst_delta_eve_to_tier1']):>10}{s['net_income']:>15,.0f}")
        sys.stdout.write(line + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
