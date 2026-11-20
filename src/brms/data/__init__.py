"""Default simulations: the scripts that build them and the zips they write.

The scripts read raw market data from ``DEFAULT_DATA_FOLDER`` (``temp/data`` at the
repository root, gitignored): ``treasury_yields.csv`` and, for the Prime-linked
banks, ``prime_rates.csv``. Each writes its zip next to itself with
:func:`brms.core.services.snapshot_writer.save_snapshot`.
"""

from pathlib import Path

DEFAULT_DATA_FOLDER = Path(__file__).resolve().parents[3] / "temp" / "data"
END_DATE = "2025-12-31"
