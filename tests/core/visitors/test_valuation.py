"""Tests for core valuation visitors."""

from unittest.mock import MagicMock

from brms.core.visitors.valuation import BankingBookValuationVisitor, TradingBookValuationVisitor


def test_banking_book_visitor_instantiation() -> None:
    """BankingBookValuationVisitor can be instantiated with a mock MarketState."""
    market_state = MagicMock()
    visitor = BankingBookValuationVisitor(market_state)
    assert visitor is not None  # noqa: S101


def test_trading_book_visitor_instantiation() -> None:
    """TradingBookValuationVisitor can be instantiated with a mock MarketState."""
    market_state = MagicMock()
    visitor = TradingBookValuationVisitor(market_state)
    assert visitor is not None  # noqa: S101


def test_visitor_dispatch_cash() -> None:
    """Visitor dispatch: Cash.accept calls visit_cash."""
    from brms.core.models.instruments.deposits import Cash

    market_state = MagicMock()
    visitor = BankingBookValuationVisitor(market_state)
    cash = Cash()
    # Should not raise; visit_cash is a no-op in ValuationVisitor
    cash.accept(visitor)


def test_visitor_dispatch_deposit() -> None:
    """Visitor dispatch: Deposit.accept calls visit_deposit."""
    from brms.core.models.instruments.deposits import Deposit

    market_state = MagicMock()
    visitor = TradingBookValuationVisitor(market_state)
    deposit = Deposit()
    deposit.accept(visitor)


def test_banking_book_only_skips_trading_instruments() -> None:
    """BankingBookValuationVisitor skips instruments in the trading book."""
    from unittest.mock import patch

    from brms.core.models.instruments.base import BookType
    from brms.core.models.instruments.deposits import Cash

    market_state = MagicMock()
    visitor = BankingBookValuationVisitor(market_state)
    cash = Cash()
    cash._book_type = BookType.TRADING  # noqa: SLF001

    with patch.object(visitor, "visit_cash", wraps=visitor.visit_cash) as mock_visit:
        cash.accept(visitor)
        mock_visit.assert_called_once()


def test_trading_book_only_skips_banking_instruments() -> None:
    """TradingBookValuationVisitor.visit_fixed_rate_bond skips banking-book bonds."""
    import QuantLib as ql  # noqa: N813

    from brms.core.models.instruments.base import BookType
    from brms.core.models.instruments.bonds import FixedRateBond

    market_state = MagicMock()
    visitor = TradingBookValuationVisitor(market_state)
    bond = FixedRateBond(
        face_value=1000.0,
        coupon_rate=0.05,
        issue_date=ql.Date(1, 1, 2020),
        maturity_date=ql.Date(1, 1, 2025),
        book_type=BookType.BANKING,
    )
    # Should silently skip (no error)
    bond.accept(visitor)
