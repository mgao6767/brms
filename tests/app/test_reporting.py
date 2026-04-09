"""Tests for HTMLStatementRenderer in the app layer."""

# ruff: noqa: S101


def test_render_trial_balance_returns_html() -> None:
    """Test that render_trial_balance returns HTML containing account names."""
    from brms.app.reporting import HTMLStatementRenderer

    data = [
        {"account": "Cash", "debit": 100.0, "credit": 0.0, "balance": 100.0},
        {"account": "Equity", "debit": 0.0, "credit": 100.0, "balance": 100.0},
    ]
    html = HTMLStatementRenderer().render_trial_balance(data)
    assert "Cash" in html
    assert "Equity" in html


def test_render_balance_sheet_returns_html() -> None:
    """Test that render_balance_sheet returns HTML containing account names."""
    from brms.app.reporting import HTMLStatementRenderer

    data = {
        "assets": [{"account": "Cash", "balance": 100.0}],
        "liabilities": [],
        "equity": [{"account": "Equity", "balance": 100.0}],
        "total_assets": 100.0,
        "total_liabilities": 0.0,
        "total_equity": 100.0,
    }
    html = HTMLStatementRenderer().render_balance_sheet(data)
    assert "Cash" in html
    assert "Equity" in html


def test_render_income_statement_returns_html() -> None:
    """Test that render_income_statement returns HTML containing account names and net income."""
    from brms.app.reporting import HTMLStatementRenderer

    data = {
        "income": [{"account": "Interest Income", "balance": 50.0}],
        "expenses": [{"account": "Interest Expense", "balance": 20.0}],
        "total_income": 50.0,
        "total_expenses": 20.0,
        "net_income": 30.0,
    }
    html = HTMLStatementRenderer().render_income_statement(data)
    assert "Interest Income" in html
    assert "Net Income" in html or "net_income" in html.lower()
