import datetime
import time
from functools import wraps

import QuantLib as ql
from PySide6.QtCore import QDate


def timeit(func):
    @wraps(func)
    def timed(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        print(f"{func.__name__} took {(end_time - start_time)*1000:.4f} ms")
        return result

    return timed


def qdate_to_qldate(date: QDate):
    """
    Convert a QDate object to a ql.Date object.

    Args:
        date (QDate): The QDate object to be converted.

    Returns:
        ql.Date: The converted ql.Date object.
    """
    assert isinstance(date, QDate)
    return ql.Date(date.day(), date.month(), date.year())


def qldate_to_pydate(date: ql.Date):
    """
    Converts a QuantLib date to a Python date.

    Args:
        date (ql.Date): The QuantLib date to be converted.

    Returns:
        datetime.date: The equivalent Python date.
    """
    assert isinstance(date, ql.Date)
    return datetime.date(date.year(), date.month(), date.dayOfMonth())


def pydate_to_qldate(date: datetime.date):
    """
    Converts a Python date object to a QuantLib date object.

    Args:
        date (datetime.date): The Python date object to be converted.

    Returns:
        ql.Date: The corresponding QuantLib date object.
    """

    assert isinstance(date, datetime.date)
    return ql.Date(date.day, date.month, date.year)


def qldate_to_string(date: ql.Date):
    """
    Converts a QuantLib date to a string.

    Args:
        date (ql.Date): The QuantLib date to be converted.

    Returns:
        "YYYY/MM/DD"
    """
    assert isinstance(date, ql.Date)
    return f"{date.year()}/{date.month()}/{date.dayOfMonth()}"
