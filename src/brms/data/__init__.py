"""Default simulations: the scripts that build them and the zips they write.

The scripts read raw market data from ``DEFAULT_DATA_FOLDER`` (``market/`` beside this
file, versioned): ``treasury_yields.csv`` and, for the Prime-linked banks,
``prime_rates.csv``. Each writes its zip next to itself with
:func:`brms.core.services.snapshot_writer.save_snapshot`; ``python -m brms.data.build_all``
writes all of them. The zips are gitignored build artifacts that every distribution build
requires (see ``hatch_build.py``).
"""

from pathlib import Path

DEFAULT_DATA_FOLDER = Path(__file__).resolve().parent / "market"
END_DATE = "2025-12-31"
