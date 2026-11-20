"""Build every default simulation zip from the versioned market data: ``python -m brms.data.build_all``."""

from __future__ import annotations

import sys
from pathlib import Path

from brms.data import DEFAULT_DATA_FOLDER
from brms.data.create_ci_loan_prime import create_ci_loan_prime_zip
from brms.data.create_diversified_bank import create_diversified_zip
from brms.data.create_fvtpl_bond import create_fvtpl_zip
from brms.data.create_htm_treasury import create_default_zip
from brms.data.create_mortgage import create_mortgage_zip

BUILDERS = (
    create_default_zip,
    create_fvtpl_zip,
    create_mortgage_zip,
    create_ci_loan_prime_zip,
    create_diversified_zip,
)


def build_all(data_folder: Path = DEFAULT_DATA_FOLDER) -> list[Path]:
    """Write all default simulation zips and return their paths."""
    return [build(data_folder=data_folder) for build in BUILDERS]


if __name__ == "__main__":
    folder = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DATA_FOLDER
    for path in build_all(folder):
        print(f"Created {path}")  # noqa: T201
