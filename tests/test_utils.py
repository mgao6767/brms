"""Unit tests for utility functions in the brms package."""

import datetime
import time

import pytest
import QuantLib as ql
from PySide6.QtCore import QDate

from brms.utils import pydate_to_qldate, qdate_to_qldate, qldate_to_pydate, qldate_to_string, timeit


def test_timeit_decorator():
    """Test the timeit decorator."""

    @timeit
    def sample_function():
        time.sleep(0.1)
        return "done"

    result = sample_function()
    assert result == "done"


def test_qdate_to_qldate():
    """Test the qdate_to_qldate function."""
    qdate = QDate(2023, 1, 1)
    qldate = qdate_to_qldate(qdate)
    assert qldate == ql.Date(1, 1, 2023)


def test_qldate_to_pydate():
    """Test the qldate_to_pydate function."""
    qldate = ql.Date(1, 12, 2023)
    pydate = qldate_to_pydate(qldate)
    assert pydate == datetime.date(2023, 12, 1)


def test_pydate_to_qldate():
    """Test the pydate_to_qldate function."""
    pydate = datetime.date(2023, 1, 1)
    qldate = pydate_to_qldate(pydate)
    assert qldate == ql.Date(1, 1, 2023)


def test_qldate_to_string():
    """Test the qldate_to_string function."""
    qldate = ql.Date(1, 2, 2023)
    date_str = qldate_to_string(qldate)
    assert date_str == "2023/2/1"


if __name__ == "__main__":
    pytest.main([__file__])
