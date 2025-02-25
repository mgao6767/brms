"""Module for schemas in the BRMS."""

from brms.models.base import ScenarioData

SCHEMA = {
    ScenarioData.TREASURY_YIELDS.value: {
        "columns": [
            "date",
            "1 Mo",
            "2 Mo",
            "3 Mo",
            "4 Mo",
            "6 Mo",
            "1 Yr",
            "2 Yr",
            "3 Yr",
            "5 Yr",
            "7 Yr",
            "10 Yr",
            "20 Yr",
            "30 Yr",
        ],
        "dtypes": {
            "date": "datetime64",
            "1 Mo": "float64",
            "2 Mo": "float64",
            "3 Mo": "float64",
            "4 Mo": "float64",
            "6 Mo": "float64",
            "1 Yr": "float64",
            "2 Yr": "float64",
            "3 Yr": "float64",
            "5 Yr": "float64",
            "7 Yr": "float64",
            "10 Yr": "float64",
            "20 Yr": "float64",
            "30 Yr": "float64",
        },
    }
}
