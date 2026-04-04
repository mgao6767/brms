"""ValuationService: selects and applies valuation visitors by book type."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from brms.core.models.instruments.base import BookType, Instrument
from brms.core.visitors.valuation import BankingBookValuationVisitor, TradingBookValuationVisitor

if TYPE_CHECKING:
    from brms.core.models.books import BankingBook, TradingBook
    from brms.core.models.market_data import MarketState
    from brms.core.visitors.base import Visitor


class ValuationService:
    """Selects the appropriate valuation visitor (strategy) based on book type."""

    _strategies: ClassVar[dict[BookType, type[Visitor]]] = {
        BookType.BANKING: BankingBookValuationVisitor,
        BookType.TRADING: TradingBookValuationVisitor,
    }

    def value_instrument(
        self,
        instrument: Instrument,
        book_type: BookType,
        market_state: MarketState,
    ) -> Any:  # noqa: ANN401
        """Value a single instrument using the visitor for the given book type."""
        visitor_cls = self._strategies[book_type]
        visitor = visitor_cls(market_state)
        return instrument.accept(visitor)

    def value_book(self, book: BankingBook | TradingBook, market_state: MarketState) -> list[Any]:
        """Value all instruments in a book, returning a list of values."""
        return [self.value_instrument(inst, book.book_type, market_state) for inst in book]
