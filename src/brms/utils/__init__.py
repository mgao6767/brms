import datetime

import QuantLib as ql
from PySide6.QtCore import QDate


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
