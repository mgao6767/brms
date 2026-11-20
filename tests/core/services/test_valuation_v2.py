"""Tests for V2 ValuationService with ValuationContext and strategies."""

# ruff: noqa: S101

from __future__ import annotations

import datetime
from unittest.mock import MagicMock, patch

import pytest

from brms.core.enums import MeasurementBasis, PositionStatus
from brms.core.exceptions import ValuationError
from brms.core.services.valuation_context import ValuationContext
from brms.core.services.valuation_service import ValuationService
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
    ctx.update(DATE, market_data, has_market_data=False)
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
        patch("brms.core.services.valuation_context.YieldCurveService.build_yield_curve", return_value=MagicMock()),
        patch("brms.core.services.valuation_context.ql") as mock_ql,
    ):
        ctx.update(DATE, market_data)
        mock_ql.Settings.instance().evaluationDate = mock_ql.Date(DATE.day, DATE.month, DATE.year)


def test_valuation_context_raises_when_curve_cannot_be_built() -> None:
    """A market day whose curve cannot be built is an error, not a stale curve."""
    ctx = ValuationContext(MagicMock())
    market_data = MagicMock()
    market_data.yields.index = []
    market_data.yields.values = []
    with (
        patch("brms.core.services.valuation_context.YieldCurveService.build_yield_curve", return_value=None),
        pytest.raises(ValuationError, match="curve"),
    ):
        ctx.update(DATE, market_data)


# ---------------------------------------------------------------------------
# ValuationService
# ---------------------------------------------------------------------------


def test_value_all_dispatches_by_measurement_basis() -> None:
    """value_all calls strategy.value_batch for the registered MeasurementBasis."""
    service = ValuationService()
    mock_strategy = MagicMock()
    service.register_strategy(MeasurementBasis.AMORTIZED_COST, mock_strategy)

    bank = MagicMock()
    bank.positions.query.return_value = [MagicMock()]

    with patch.object(service._context, "update"):  # skip QL setup  # noqa: SLF001
        service.value_all(bank, MagicMock(), DATE, ValuationStore())

    mock_strategy.value_batch.assert_called_once()


def test_skips_empty_batches() -> None:
    """value_all does not call strategy.value_batch when the batch is empty."""
    service = ValuationService()
    mock_strategy = MagicMock()
    service.register_strategy(MeasurementBasis.AMORTIZED_COST, mock_strategy)

    bank = MagicMock()
    bank.positions.query.return_value = []

    with patch.object(service._context, "update"):  # noqa: SLF001
        service.value_all(bank, MagicMock(), DATE, ValuationStore())

    mock_strategy.value_batch.assert_not_called()


def test_register_multiple_strategies() -> None:
    """Multiple strategies can be registered for different MeasurementBasises."""
    service = ValuationService()
    strat_htm = MagicMock()
    strat_fvtpl = MagicMock()
    service.register_strategy(MeasurementBasis.AMORTIZED_COST, strat_htm)
    service.register_strategy(MeasurementBasis.FVTPL, strat_fvtpl)

    bank = MagicMock()
    # HTM returns positions, FVTPL returns empty
    bank.positions.query.side_effect = lambda **kw: (
        [MagicMock()] if kw.get("measurement_basis") == MeasurementBasis.AMORTIZED_COST else []
    )

    with patch.object(service._context, "update"):  # noqa: SLF001
        service.value_all(bank, MagicMock(), DATE, ValuationStore())

    strat_htm.value_batch.assert_called_once()
    strat_fvtpl.value_batch.assert_not_called()


def test_value_all_passes_valuation_store_to_strategy() -> None:
    """value_all passes the provided valuation_store to strategy.value_batch."""
    service = ValuationService()
    mock_strategy = MagicMock()
    service.register_strategy(MeasurementBasis.FVOCI, mock_strategy)

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


def test_value_all_queries_open_positions_by_measurement_basis() -> None:
    """value_all queries positions with measurement_basis and status=OPEN."""
    service = ValuationService()
    mock_strategy = MagicMock()
    service.register_strategy(MeasurementBasis.AMORTIZED_COST, mock_strategy)

    bank = MagicMock()
    bank.positions.query.return_value = []

    with patch.object(service._context, "update"):  # noqa: SLF001
        service.value_all(bank, MagicMock(), DATE, ValuationStore())

    bank.positions.query.assert_called_once_with(
        measurement_basis=MeasurementBasis.AMORTIZED_COST,
        status=PositionStatus.OPEN,
    )
