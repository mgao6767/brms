"""Module for data loader."""

import os
from abc import ABC, abstractmethod

import pandas as pd

from brms.data.schema import SCHEMA
from brms.models.base import ScenarioData


class DataLoader(ABC):
    """Abstract base class for data loaders."""

    @abstractmethod
    def load(self) -> pd.DataFrame:
        pass


class CSVLoader(DataLoader):
    """Load simulation data from CSV files in a specified folder, based on SCHEMA."""

    def __init__(self, folder_path):
        self.folder_path = folder_path

    def load_treasury_yields(self):
        return self._load_csv(ScenarioData.TREASURY_YIELDS.value)

    def _load_csv(self, file_key):
        """Load a CSV file and validates it against the schema."""
        if file_key not in SCHEMA:
            raise ValueError(f"Dataset '{file_key}' is not defined in SCHEMA.")

        file_path = os.path.join(self.folder_path, f"{file_key}.csv")
        if not os.path.exists(file_path):
            print(f"Warning: {file_key}.csv not found! Skipping.")
            return None

        # Identify date columns from schema
        date_columns = [col for col, dtype in SCHEMA[file_key]["dtypes"].items() if dtype == "datetime64"]

        # Load CSV with dynamic date parsing
        df = pd.read_csv(file_path, parse_dates=date_columns if date_columns else None)

        # Validate columns
        expected_columns = SCHEMA[file_key]["columns"]
        if list(df.columns) != expected_columns:
            error = f"Column mismatch in {file_key}.csv. Expected: {expected_columns}, Found: {list(df.columns)}"
            raise ValueError(error)

        # Convert data types & handle NaNs
        dtype_map = SCHEMA[file_key]["dtypes"]
        for col, dtype in dtype_map.items():
            if col in df.columns:
                df[col] = df[col].astype(dtype, errors="ignore")  # Safe conversion

        return df

    def load(self):
        """Loads all data."""
        return {
            ScenarioData.TREASURY_YIELDS: self._load_csv(ScenarioData.TREASURY_YIELDS.value),
        }


class DataLoaderFactory:
    @staticmethod
    def get_loader(source_type, source_path_or_conn) -> DataLoader:
        if source_type == "csv":
            return CSVLoader(source_path_or_conn)
        raise ValueError("Unsupported data source type.")


if __name__ == "__main__":
    import time
    import QuantLib as ql
    from brms.services.yield_curve_service import YieldCurveService
    from brms.utils import pydate_to_qldate

    current_file_path = os.path.dirname(os.path.abspath(__file__))
    data_folder_path = os.path.join(current_file_path, "./default")
    data_loader = DataLoaderFactory.get_loader("csv", data_folder_path)
    data = data_loader.load()
    yield_df = data[ScenarioData.TREASURY_YIELDS]

    start_time = time.time()
    maturity_labels = [col for col in yield_df.columns if col != "date"]  # Exclude Date column
    test_maturities = [1, 2, 3, 5, 7, 10, 20, 30]
    calendar = ql.ActualActual(ql.ActualActual.ISDA)
    for index, latest_row in yield_df.iterrows():
        # Extract reference date and maturity data
        ref_date = latest_row["date"].date()  # Python datetime.date
        rates = [latest_row[col] for col in maturity_labels]  # Convert rates to list
        term_structure = YieldCurveService.build_yield_curve(ref_date, maturity_labels, rates)
        assert isinstance(term_structure, ql.TermStructure)
        # Test the zero rates at various maturities
        zero_rates = [
            term_structure.zeroRate(
                pydate_to_qldate(ref_date) + ql.Period(m, ql.Years), calendar, ql.Compounded, ql.Annual
            ).rate()
            * 100
            for m in test_maturities
        ]
    end_time = time.time()
    print(f"Total yield curves built: {index+1}")
    print(f"Total zero rates computed: {(index+1) * len(test_maturities)}")
    print(f"Total execution time: {end_time - start_time} seconds")
