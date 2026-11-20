"""Hatch build hook: refuse to build a distribution without the default simulation zips.

The zips are generated (``python -m brms.data.build_all``) and gitignored, so a build from a
fresh checkout would otherwise silently ship a package that cannot open any simulation.
Editable installs (``uv sync``) are not checked.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

SIMULATIONS = (
    "htm_treasury", "fvtpl_bond", "mortgage", "ci_loan_prime", "diversified_bank",
    "case_svb_2021", "case_svb_2022", "case_signature_2021", "case_first_republic_2021", "case_jpmorgan_chase_2021",
)


def require_simulation_zips(root: Path) -> None:
    """Raise RuntimeError naming any default simulation zip missing under *root*."""
    data = root / "src" / "brms" / "data"
    missing = [name for name in SIMULATIONS if not (data / f"{name}.zip").exists()]
    if missing:
        msg = f"Missing simulation zips {missing}; run `python -m brms.data.build_all` before building"
        raise RuntimeError(msg)


class CustomBuildHook(BuildHookInterface):
    """Check the simulation zips before a standard (non-editable) build."""

    def initialize(self, version: str, build_data: dict[str, Any]) -> None:  # noqa: ARG002
        """Run the check unless this is an editable install."""
        if version != "editable":
            require_simulation_zips(Path(self.root))
