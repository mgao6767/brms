"""Packaging: the core is usable headless, and the wheel ships its data."""

from __future__ import annotations

import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from brms.core.exceptions import SimulationDataError
from brms.core.services import build_core_services

_GUI_PACKAGES = {"PySide6", "qtawesome", "matplotlib"}
_SHIPPED = ("htm_treasury", "fvtpl_bond", "mortgage", "ci_loan_prime", "diversified_bank")
_REPO = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def wheel(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Build the wheel once for the module."""
    out = tmp_path_factory.mktemp("wheel")
    subprocess.run(  # noqa: S603
        ["uv", "build", "--wheel", "--out-dir", str(out)],  # noqa: S607
        cwd=_REPO,
        check=True,
        capture_output=True,
    )
    return next(out.glob("*.whl"))


def test_core_import_does_not_load_gui() -> None:
    """Importing the core services must not pull in any GUI package."""
    code = (
        "import sys, brms.core.services\n"
        f"bad = [m for m in sys.modules if m.split('.')[0] in {_GUI_PACKAGES!r}]\n"
        "assert not bad, bad\n"
    )
    assert subprocess.run([sys.executable, "-c", code], check=False).returncode == 0  # noqa: S101, S603


def test_wheel_ships_simulation_zips(wheel: Path) -> None:
    """The default simulations must be inside the wheel."""
    names = zipfile.ZipFile(wheel).namelist()
    for name in _SHIPPED:
        assert f"brms/data/{name}.zip" in names  # noqa: S101


def test_wheel_core_requirements_exclude_gui(wheel: Path) -> None:
    """Unconditional requirements are pandas and quantlib only."""
    with zipfile.ZipFile(wheel) as zf:
        meta_name = next(n for n in zf.namelist() if n.endswith(".dist-info/METADATA"))
        meta = zf.read(meta_name).decode()
    required = {
        line.split(":", 1)[1].strip().split(";")[0].split(">")[0].split("=")[0].split("<")[0].strip().lower()
        for line in meta.splitlines()
        if line.startswith("Requires-Dist:") and "extra ==" not in line
    }
    assert required == {"pandas", "quantlib"}  # noqa: S101


def test_missing_simulation_zip_raises(tmp_path: Path) -> None:
    """A missing simulation file is an error, not a silently empty bank."""
    with pytest.raises(SimulationDataError, match="not found"):
        build_core_services(simulation_zip=tmp_path / "nope.zip")


def _hatch_hook_module():  # noqa: ANN202
    import importlib.util

    spec = importlib.util.spec_from_file_location("hatch_build", _REPO / "hatch_build.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_raw_market_data_is_versioned() -> None:
    """The default simulations can be rebuilt from a clean checkout."""
    from brms.data import DEFAULT_DATA_FOLDER

    tracked = subprocess.run(  # noqa: S603
        ["git", "ls-files", str(DEFAULT_DATA_FOLDER)],  # noqa: S607
        cwd=_REPO, check=True, capture_output=True, text=True,
    ).stdout.split()
    assert {Path(p).name for p in tracked} >= {"treasury_yields.csv", "prime_rates.csv"}  # noqa: S101


def test_build_fails_without_simulation_zips(tmp_path: Path) -> None:
    """A distribution build refuses to produce a package without its default simulations."""
    hook = _hatch_hook_module()
    (tmp_path / "src" / "brms" / "data").mkdir(parents=True)
    with pytest.raises(RuntimeError, match=r"python -m brms\.data\.build_all"):
        hook.require_simulation_zips(tmp_path)
