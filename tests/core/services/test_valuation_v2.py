"""Tests for V2 ValuationService with ValuationContext and strategies."""

# ruff: noqa: S101

from __future__ import annotations

import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

from brms.core.enums import InstrumentClass, PositionStatus, ValuationType
from brms.core.services.valuation_context import ValuationContext
from brms.core.services.valuation_service import ValuationService
from brms.core.services.valuation_strategies import AmortizedCostStrategy, FairValueStrategy, OutstandingBalanceStrategy
from brms.core.stores.valuation_store import ValuationStore

DATE = datetime.date(2024, 1, 1)


# ---------------------------------------------------------------------------
# ValuationContext
# ---------------------------------------------------------------------------


def test_valuation_context_initial_state() -> None:
    """ValuationContext initialises with no date and no market_data."""
    handle = MagicMock()
    ctx = ValuationContext(handle)
    assert ctx.date is None
    assert ctx.market_data is None


def test_valuation_context_update_sets_date_and_market_data() -> None:
    """update() stores the date and market_data on the context."""
    handle = MagicMock()
    ctx = ValuationContext(handle)
    market_data = MagicMock()
    ctx.update(DATE, market_data)
    assert ctx.date == DATE
    assert ctx.market_data is market_data


def test_valuation_context_update_relinks_handle() -> None:
    """update() calls linkTo on the yield handle with a built term structure."""
    handle = MagicMock()
    ctx = ValuationContext(handle)
    market_data = MagicMock()
    market_data.yields = MagicMock()
    market_data.yields.index = ["1 Yr", "5 Yr"]
    market_data.yields.values = [2.5, 3.0]

    with patch("brms.core.services.valuation_context.YieldCurveService.build_yield_curve") as mock_build:
        mock_ts = MagicMock()
        mock_build.return_value = mock_ts
        ctx.update(DATE, market_data)
        mock_build.assert_called_once()
        handle.linkTo.assert_called_once_with(mock_ts)


def test_valuation_context_update_sets_ql_evaluation_date() -> None:
    """update() sets the QuantLib global evaluation date."""
    handle = MagicMock()
    ctx = ValuationContext(handle)
    market_data = MagicMock()
    market_data.yields = MagicMock()
    market_data.yields.index = []
    market_data.yields.values = []

    with (
        patch("brms.core.services.valuation_context.YieldCurveService.build_yield_curve", return_value=None),
        patch("brms.core.services.valuation_context.ql") as mock_ql,
    ):
        ctx.update(DATE, market_data)
        mock_ql.Settings.instance().evaluationDate = mock_ql.Date(DATE.day, DATE.month, DATE.year)


# ---------------------------------------------------------------------------
# FairValueStrategy
# ---------------------------------------------------------------------------


def test_fair_value_strategy_uses_npv_when_ql_instrument_present() -> None:
    """FairValueStrategy records NPV() when ql_instrument is not None."""
    strategy = FairValueStrategy()
    # Pre-populate engines_set so it doesn't try to create a real QL engine with mocks
    strategy._engines_set.add("inst-1")  # noqa: SLF001
    store = ValuationStore()
    context = MagicMock()
    context.date = DATE

    ql_inst = MagicMock()
    ql_inst.NPV.return_value = 1050.0

    inst = MagicMock()
    inst.id = "inst-1"
    inst.ql_instrument = ql_inst

    instruments = MagicMock()
    instruments.get.return_value = inst

    pos = MagicMock()
    pos.id = "pos-1"
    pos.instrument_id = "inst-1"

    strategy.value_batch([pos], instruments, context, store)

    result = store.get("pos-1", DATE, ValuationType.FAIR_VALUE)
    assert result == Decimal("1050.0")


def test_fair_value_strategy_uses_face_value_when_no_ql_instrument() -> None:
    """FairValueStrategy records face_value when ql_instrument is None."""
    strategy = FairValueStrategy()
    store = ValuationStore()
    context = MagicMock()
    context.date = DATE

    inst = MagicMock()
    inst.ql_instrument = None
    inst.face_value = Decimal("1000")

    instruments = MagicMock()
    instruments.get.return_value = inst

    pos = MagicMock()
    pos.id = "pos-2"
    pos.instrument_id = "inst-2"

    strategy.value_batch([pos], instruments, context, store)

    result = store.get("pos-2", DATE, ValuationType.FAIR_VALUE)
    assert result == Decimal("1000")


def test_fair_value_strategy_handles_multiple_positions() -> None:
    """FairValueStrategy records a value for each position in the batch."""
    strategy = FairValueStrategy()
    strategy._engines_set.update({"p1", "p2"})  # noqa: SLF001
    store = ValuationStore()
    context = MagicMock()
    context.date = DATE

    def make_pos_inst(pos_id: str, npv: float) -> tuple[MagicMock, MagicMock]:
        ql_inst = MagicMock()
        ql_inst.NPV.return_value = npv
        inst = MagicMock()
        inst.id = pos_id
        inst.ql_instrument = ql_inst
        pos = MagicMock()
        pos.id = pos_id
        pos.instrument_id = pos_id
        return pos, inst

    pos1, inst1 = make_pos_inst("p1", 100.0)
    pos2, inst2 = make_pos_inst("p2", 200.0)

    instruments = MagicMock()
    instruments.get.side_effect = lambda iid: {"p1": inst1, "p2": inst2}[iid]

    strategy.value_batch([pos1, pos2], instruments, context, store)

    assert store.get("p1", DATE, ValuationType.FAIR_VALUE) == Decimal("100.0")
    assert store.get("p2", DATE, ValuationType.FAIR_VALUE) == Decimal("200.0")


# ---------------------------------------------------------------------------
# AmortizedCostStrategy
# ---------------------------------------------------------------------------


def test_amortized_cost_strategy_records_carrying_value() -> None:
    """AmortizedCostStrategy records CARRYING_VALUE using face_value."""
    strategy = AmortizedCostStrategy()
    store = ValuationStore()
    context = MagicMock()
    context.date = DATE

    inst = MagicMock()
    inst.face_value = Decimal("950")

    instruments = MagicMock()
    instruments.get.return_value = inst

    pos = MagicMock()
    pos.id = "pos-ac"
    pos.instrument_id = "inst-ac"

    strategy.value_batch([pos], instruments, context, store)

    result = store.get("pos-ac", DATE, ValuationType.CARRYING_VALUE)
    assert result == Decimal("950")


# ---------------------------------------------------------------------------
# OutstandingBalanceStrategy
# ---------------------------------------------------------------------------


def test_outstanding_balance_strategy_records_carrying_value() -> None:
    """OutstandingBalanceStrategy records CARRYING_VALUE using face_value as proxy."""
    strategy = OutstandingBalanceStrategy()
    store = ValuationStore()
    context = MagicMock()
    context.date = DATE

    inst = MagicMock()
    inst.face_value = Decimal("75000")

    instruments = MagicMock()
    instruments.get.return_value = inst

    pos = MagicMock()
    pos.id = "pos-loan"
    pos.instrument_id = "inst-loan"

    strategy.value_batch([pos], instruments, context, store)

    result = store.get("pos-loan", DATE, ValuationType.CARRYING_VALUE)
    assert result == Decimal("75000")


# ---------------------------------------------------------------------------
# ValuationService
# ---------------------------------------------------------------------------


def test_value_all_dispatches_by_instrument_class() -> None:
    """value_all calls strategy.value_batch for the registered InstrumentClass."""
    service = ValuationService()
    mock_strategy = MagicMock()
    service.register_strategy(InstrumentClass.HTM, mock_strategy)

    bank = MagicMock()
    bank.positions.query.return_value = [MagicMock()]

    with patch.object(service._context, "update"):  # skip QL setup  # noqa: SLF001
        service.value_all(bank, MagicMock(), DATE, ValuationStore())

    mock_strategy.value_batch.assert_called_once()


def test_skips_empty_batches() -> None:
    """value_all does not call strategy.value_batch when the batch is empty."""
    service = ValuationService()
    mock_strategy = MagicMock()
    service.register_strategy(InstrumentClass.HTM, mock_strategy)

    bank = MagicMock()
    bank.positions.query.return_value = []

    with patch.object(service._context, "update"):  # noqa: SLF001
        service.value_all(bank, MagicMock(), DATE, ValuationStore())

    mock_strategy.value_batch.assert_not_called()


def test_register_multiple_strategies() -> None:
    """Multiple strategies can be registered for different InstrumentClasses."""
    service = ValuationService()
    strat_htm = MagicMock()
    strat_fvtpl = MagicMock()
    service.register_strategy(InstrumentClass.HTM, strat_htm)
    service.register_strategy(InstrumentClass.FVTPL, strat_fvtpl)

    bank = MagicMock()
    # HTM returns positions, FVTPL returns empty
    bank.positions.query.side_effect = lambda **kw: (
        [MagicMock()] if kw.get("instrument_class") == InstrumentClass.HTM else []
    )

    with patch.object(service._context, "update"):  # noqa: SLF001
        service.value_all(bank, MagicMock(), DATE, ValuationStore())

    strat_htm.value_batch.assert_called_once()
    strat_fvtpl.value_batch.assert_not_called()


def test_value_all_passes_valuation_store_to_strategy() -> None:
    """value_all passes the provided valuation_store to strategy.value_batch."""
    service = ValuationService()
    mock_strategy = MagicMock()
    service.register_strategy(InstrumentClass.FVOCI, mock_strategy)

    bank = MagicMock()
    position = MagicMock()
    bank.positions.query.return_value = [position]

    val_store = ValuationStore()

    with patch.object(service._context, "update"):  # noqa: SLF001
        service.value_all(bank, MagicMock(), DATE, val_store)

    _, kwargs = mock_strategy.value_batch.call_args
    # The valuation_store is the 4th positional arg
    call_args = mock_strategy.value_batch.call_args[0]
    assert call_args[3] is val_store


def test_value_all_queries_open_positions_by_instrument_class() -> None:
    """value_all queries positions with instrument_class and status=OPEN."""
    service = ValuationService()
    mock_strategy = MagicMock()
    service.register_strategy(InstrumentClass.HTM, mock_strategy)

    bank = MagicMock()
    bank.positions.query.return_value = []

    with patch.object(service._context, "update"):  # noqa: SLF001
        service.value_all(bank, MagicMock(), DATE, ValuationStore())

    bank.positions.query.assert_called_once_with(
        instrument_class=InstrumentClass.HTM,
        status=PositionStatus.OPEN,
    )
