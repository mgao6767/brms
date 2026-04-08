"""Qt date conversion utilities."""

import datetime

import QuantLib as ql  # noqa: N813
from PySide6.QtCore import QDate


def qdate_to_qldate(date: QDate) -> ql.Date:
    """Convert a QDate to a QuantLib Date."""
    return ql.Date(date.day(), date.month(), date.year())


def pydate_to_qdate(date: datetime.date) -> QDate:
    """Convert a Python date to a QDate."""
    return QDate(date.year, date.month, date.day)
