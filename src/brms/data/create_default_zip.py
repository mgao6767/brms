"""Generate the default simulation zip archive (v2 format).

This script builds ``default_simulation.zip`` containing:

* ``config.json``       -- simulation configuration.
* ``instruments.json``  -- instrument definitions with constructor kwargs.
* ``positions.json``    -- one position per instrument.
* ``yields.csv``        -- historical yield curve data.

Run with::

    uv run python src/brms/data/create_default_zip.py

"""

from __future__ import annotations

import json
import random
import uuid
import zipfile
from datetime import date
from pathlib import Path

from dateutil.relativedelta import relativedelta

# Seed for reproducibility -- same as the old default/__init__.py
random.seed(42)

_DATA_DIR = Path(__file__).resolve().parent
_OUT_PATH = _DATA_DIR / "default_simulation.zip"
_YIELDS_CSV = _DATA_DIR / "default" / "treasury_yields.csv"

_START_DATE = "2022-01-03"


def _issuer_dict(name: str, issuer_type: str, credit_rating: str = "UNRATED") -> dict:
    return {"name": name, "issuer_type": issuer_type, "credit_rating": credit_rating}


def _build_instruments_and_positions() -> tuple[list[dict], list[dict]]:
    """Build the instruments.json and positions.json structures."""
    instruments: list[dict] = []
    positions: list[dict] = []

    def _add(
        inst: dict, book_type: str, measurement_basis: str, acquisition_cost: float,
        side: str = "LONG",
    ) -> None:
        inst_id = str(uuid.uuid4())
        inst["id"] = inst_id
        instruments.append(inst)
        positions.append({
            "id": str(uuid.uuid4()),
            "instrument_id": inst_id,
            "book_type": book_type,
            "measurement_basis": measurement_basis,
            "side": side,
            "acquisition_date": _START_DATE,
            "acquisition_cost": acquisition_cost,
        })

    # 1. CommonEquity (1,000,000) — liability side (SHORT)
    _add(
        {"type": "common_equity", "name": "Common Equity"},
        book_type="BANKING",
        measurement_basis="NA",
        acquisition_cost=1_000_000,
        side="SHORT",
    )

    # 2. Deposit (6,000,000) — liability side (SHORT)
    _add(
        {"type": "deposit", "name": "Deposit"},
        book_type="BANKING",
        measurement_basis="NA",
        acquisition_cost=6_000_000,
        side="SHORT",
    )

    # 3. HTM TreasuryNote (10,000 face, 5% coupon)
    _add(
        {
            "type": "treasury_note",
            "face_value": 10_000.0,
            "coupon_rate": 0.05,
            "issue_date": "2020-01-01",
            "maturity_date": "2030-01-01",
            "measurement_basis": "AMORTIZED_COST",
            "credit_rating": "AAA",
            "issuer": _issuer_dict("Government", "SOVEREIGN", "AAA"),
        },
        book_type="BANKING",
        measurement_basis="AMORTIZED_COST",
        acquisition_cost=10_000.0,
    )

    # 4. Five residential mortgages (200k-500k, random rates/terms)
    for _i in range(5):
        face_value = 200_000 + 100_000 * random.randint(1, 3)  # noqa: S311
        interest_rate = 0.05 + 0.01 * random.randint(0, 3)  # noqa: S311
        months_offset = random.randint(0, 24)  # noqa: S311
        issue = date(2020, 10, 1) + relativedelta(months=months_offset)
        maturity_years = random.choice([10, 20, 30])  # noqa: S311

        _add(
            {
                "type": "residential_mortgage",
                "face_value": float(face_value),
                "interest_rate": interest_rate,
                "issue_date": issue.isoformat(),
                "maturity": f"{maturity_years}Y",
                "measurement_basis": "AMORTIZED_COST",
                "credit_rating": "UNRATED",
                "issuer": _issuer_dict("Residential Mortgage Issuer", "INDIVIDUAL"),
            },
            book_type="BANKING",
            measurement_basis="AMORTIZED_COST",
            acquisition_cost=float(face_value),
        )

    # 5. Ten FVOCI TreasuryNotes (100k each)
    for _i in range(10):
        coupon_rate = 0.0125 * random.randint(1, 5)  # noqa: S311
        years = random.choice([2, 3, 5, 7, 10])  # noqa: S311
        mat = date(2020, 1, 1) + relativedelta(years=years)
        _add(
            {
                "type": "treasury_note",
                "face_value": 100_000.0,
                "coupon_rate": coupon_rate,
                "issue_date": "2020-01-01",
                "maturity_date": mat.isoformat(),
                "measurement_basis": "FVOCI",
                "credit_rating": "AAA",
                "issuer": _issuer_dict("Government", "SOVEREIGN", "AAA"),
            },
            book_type="BANKING",
            measurement_basis="FVOCI",
            acquisition_cost=100_000.0,
        )

    # 6. Ten FVTPL TreasuryNotes (100k each, trading book)
    for _i in range(10):
        coupon_rate = 0.0125 * random.randint(1, 5)  # noqa: S311
        years = random.choice([2, 3, 5, 7, 10])  # noqa: S311
        mat = date(2020, 1, 1) + relativedelta(years=years)
        _add(
            {
                "type": "treasury_note",
                "face_value": 100_000.0,
                "coupon_rate": coupon_rate,
                "issue_date": "2020-01-01",
                "maturity_date": mat.isoformat(),
                "measurement_basis": "FVTPL",
                "book_type": "trading",
                "credit_rating": "AAA",
                "issuer": _issuer_dict("Government", "SOVEREIGN", "AAA"),
            },
            book_type="TRADING",
            measurement_basis="FVTPL",
            acquisition_cost=100_000.0,
        )

    return instruments, positions


def create_default_zip(out_path: Path | None = None) -> Path:
    """Write the default simulation zip to *out_path* and return its path."""
    out_path = out_path or _OUT_PATH
    instruments, pos = _build_instruments_and_positions()

    config = {
        "name": "Default Bank",
        "replay_from": _START_DATE,
        "start_date": _START_DATE,
    }

    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("config.json", json.dumps(config, indent=2))
        zf.writestr("instruments.json", json.dumps(instruments, indent=2))
        zf.writestr("positions.json", json.dumps(pos, indent=2))

        # Copy the treasury yields CSV as yields.csv
        if _YIELDS_CSV.exists():
            zf.write(_YIELDS_CSV, "yields.csv")
        else:
            msg = f"Treasury yields CSV not found at {_YIELDS_CSV}"
            raise FileNotFoundError(msg)

    return out_path


if __name__ == "__main__":
    path = create_default_zip()
    print(f"Created {path}")  # noqa: T201
