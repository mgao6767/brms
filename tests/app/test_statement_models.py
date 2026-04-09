"""Tests for statement table models."""

# ruff: noqa: S101, D103, PLR2004

from PySide6.QtCore import Qt

from brms.app.models.statement_models import TrialBalanceModel


def test_trial_balance_model_empty() -> None:
    model = TrialBalanceModel()
    assert model.rowCount() == 0
    assert model.columnCount() == 3


def test_trial_balance_model_columns() -> None:
    model = TrialBalanceModel()
    assert model.headerData(0, Qt.Horizontal) == "Account"
    assert model.headerData(1, Qt.Horizontal) == "Debit"
    assert model.headerData(2, Qt.Horizontal) == "Credit"


def test_trial_balance_model_update() -> None:
    model = TrialBalanceModel()
    data = [
        {"account": "Cash", "debit": 1000.0, "credit": 0.0, "balance": 1000.0},
        {"account": "Equity", "debit": 0.0, "credit": 1000.0, "balance": 1000.0},
    ]
    model.update(data)
    # 2 account rows + 1 totals row
    assert model.rowCount() == 3
    # First row
    assert model.data(model.index(0, 0)) == "Cash"
    assert model.data(model.index(0, 1)) == 1000.0
    assert model.data(model.index(0, 2)) == 0.0
    # Totals row
    assert model.data(model.index(2, 0)) == "Total"
    assert model.data(model.index(2, 1)) == 1000.0
    assert model.data(model.index(2, 2)) == 1000.0


def test_trial_balance_model_skips_zero_rows() -> None:
    model = TrialBalanceModel()
    data = [
        {"account": "Cash", "debit": 1000.0, "credit": 0.0, "balance": 1000.0},
        {"account": "Empty", "debit": 0.0, "credit": 0.0, "balance": 0.0},
    ]
    model.update(data)
    # 1 account row + 1 totals row (zero row skipped)
    assert model.rowCount() == 2


def test_trial_balance_bold_role_on_totals() -> None:
    model = TrialBalanceModel()
    data = [
        {"account": "Cash", "debit": 100.0, "credit": 0.0, "balance": 100.0},
    ]
    model.update(data)
    # Row 0 (account) — not bold
    assert model.data(model.index(0, 0), Qt.UserRole) is not True
    # Row 1 (totals) — bold
    assert model.data(model.index(1, 0), Qt.UserRole) is True


def test_trial_balance_model_update_clears_old_data() -> None:
    model = TrialBalanceModel()
    data1 = [{"account": "Cash", "debit": 100.0, "credit": 0.0, "balance": 100.0}]
    model.update(data1)
    assert model.rowCount() == 2  # 1 + totals
    data2 = [
        {"account": "A", "debit": 1.0, "credit": 0.0, "balance": 1.0},
        {"account": "B", "debit": 0.0, "credit": 1.0, "balance": 1.0},
    ]
    model.update(data2)
    assert model.rowCount() == 3  # 2 + totals
    assert model.data(model.index(0, 0)) == "A"
