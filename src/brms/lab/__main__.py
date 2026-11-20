"""Command line: ``python -m brms.lab run <simulation.zip> --scenario parallel+200 --months 12 --out results``."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

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
    args = parser.parse_args(argv)

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
