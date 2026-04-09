"""Core utility functions for date conversions and related helpers."""

import datetime

import QuantLib as ql  # noqa: N813


def pydate_to_qldate(date: datetime.date) -> ql.Date:
    """Convert a Python date object to a QuantLib date object.

    Args:
        date: The Python date object to be converted.

    Returns:
        The corresponding QuantLib date object.

    """
    return ql.Date(date.day, date.month, date.year)


def qldate_to_pydate(date: ql.Date) -> datetime.date:
    """Convert a QuantLib date to a Python date.

    Args:
        date: The QuantLib date to be converted.

    Returns:
        The equivalent Python date.

    """
    return datetime.date(date.year(), date.month(), date.dayOfMonth())


def qldate_to_string(date: ql.Date) -> str:
    """Convert a QuantLib date to a string.

    Args:
        date: The QuantLib date to be converted.

    Returns:
        A string in ``YYYY/MM/DD`` format.

    """
    return f"{date.year()}/{date.month()}/{date.dayOfMonth()}"
