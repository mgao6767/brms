"""The stress-test lab: run a bank through rate scenarios and compare the results.

>>> from brms.lab import run, Shock
>>> from brms.core.metrics.risk.interest_rate_risk.eve import Scenario
>>> result = run("bank.zip", Shock(Scenario.PARALLEL_UP), months=12)  # doctest: +SKIP
>>> result.metrics["CET1_RATIO"].plot()  # doctest: +SKIP
"""

from brms.lab.runner import RunResult, run, run_many
from brms.lab.scenarios import Historical, Shock, parse_scenario

__all__ = ["Historical", "RunResult", "Shock", "parse_scenario", "run", "run_many"]
