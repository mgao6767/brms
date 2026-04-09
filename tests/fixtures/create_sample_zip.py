"""Create a sample simulation zip for testing."""

import json
import zipfile
from pathlib import Path


def create_sample_zip(output_path: Path) -> None:
    """Generate a sample simulation zip with 30 days of yield data."""
    bank_data = {
        "name": "Sample Bank",
        "as_of_date": "2024-01-01",
        "banking_book": [],
        "trading_book": [],
        "initial_accounts": {
            "cash": 10000000,
            "common_equity": 5000000,
        },
    }
    yields_csv = "date,1M,3M,6M,1Y,2Y,5Y,10Y\n"
    for day in range(1, 31):
        date = f"2024-01-{day:02d}"
        yields_csv += f"{date},0.053,0.052,0.051,0.048,0.046,0.043,0.042\n"

    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("bank.json", json.dumps(bank_data, indent=2))
        zf.writestr("yields.csv", yields_csv)


if __name__ == "__main__":
    create_sample_zip(Path(__file__).parent / "sample_simulation.zip")
