"""ValuationService: selects and applies valuation visitors by book type."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

import QuantLib as ql  # noqa: N813

from brms.core.enums import InstrumentClass, PositionStatus
from brms.core.models.instruments.base import BookType, Instrument
from brms.core.services.valuation_context import ValuationContext
from brms.core.visitors.valuation import BankingBookValuationVisitor, TradingBookValuationVisitor

if TYPE_CHECKING:
    import datetime

    from brms.core.models.books import BankingBook, TradingBook
    from brms.core.models.market_data import MarketState
    from brms.core.services.valuation_strategies import ValuationStrategy
    from brms.core.stores.valuation_store import ValuationStore
    from brms.core.visitors.base import Visitor


class LegacyValuationService:
    """Selects the appropriate valuation visitor (strategy) based on book type.

    .. deprecated::
        Use :class:`ValuationService` (V2) instead.
    """

    _visitor_map: ClassVar[dict[BookType, type[Visitor]]] = {
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
        visitor_cls = self._visitor_map[book_type]
        visitor = visitor_cls(market_state)
        return instrument.accept(visitor)

    def value_book(self, book: BankingBook | TradingBook, market_state: MarketState) -> list[Any]:
        """Value all instruments in a book, returning a list of values."""
        return [self.value_instrument(inst, book.book_type, market_state) for inst in book]


class ValuationService:
    """Strategy-based valuation service (V2) dispatching by InstrumentClass.

    A single :class:`ValuationContext` is shared across all strategies to avoid
    rebuilding the term structure multiple times per date.
    """

    def __init__(self) -> None:
        """Initialise with an empty strategy registry and a shared context."""
        self._yield_handle: ql.RelinkableYieldTermStructureHandle = ql.RelinkableYieldTermStructureHandle()
        self._strategies: dict[InstrumentClass, ValuationStrategy] = {}
        self._context: ValuationContext = ValuationContext(self._yield_handle)

    def register_strategy(self, instrument_class: InstrumentClass, strategy: ValuationStrategy) -> None:
        """Register *strategy* for positions of *instrument_class*."""
        self._strategies[instrument_class] = strategy

    def value_all(
        self,
        bank: object,
        market_data: object,
        date: datetime.date,
        valuation_store: ValuationStore,
    ) -> None:
        """Value all open positions in *bank*, grouped by InstrumentClass.

        Updates the shared context once for *date*, then delegates to each registered
        strategy for its corresponding InstrumentClass, skipping empty batches.
        """
        self._context.update(date, market_data)
        for instrument_class, strategy in self._strategies.items():
            positions = bank.positions.query(  # type: ignore[union-attr]
                instrument_class=instrument_class,
                status=PositionStatus.OPEN,
            )
            if positions:
                strategy.value_batch(positions, bank.instruments, self._context, valuation_store)  # type: ignore[union-attr]
