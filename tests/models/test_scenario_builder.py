"""Tests for the ScenarioBuilder class."""

import datetime

import pytest
import QuantLib as ql  # noqa: N813

from brms.models.base import ScenarioData
from brms.models.scenario import ScenarioBuilder


@pytest.fixture
def scenario_builder() -> ScenarioBuilder:
    """Fixture to create a ScenarioBuilder with a specific date."""
    date = datetime.date(2023, 1, 1)
    return ScenarioBuilder(date)


def test_initialization(scenario_builder: ScenarioBuilder) -> None:
    """Test the initialization of the ScenarioBuilder."""
    scenario = scenario_builder.build()
    assert scenario.date == datetime.date(2023, 1, 1)
    assert scenario.data == {}


def test_with_term_structure(scenario_builder: ScenarioBuilder) -> None:
    """Test adding a term structure to the Scenario."""
    today = ql.Date(1, 1, 2025)
    day_counter = ql.Actual360()
    interest_rate = 0.05
    flat_forward = ql.FlatForward(today, ql.QuoteHandle(ql.SimpleQuote(interest_rate)), day_counter)
    term_structure = ql.YieldTermStructureHandle(flat_forward)
    scenario_builder.with_term_structure(term_structure)
    scenario = scenario_builder.build()
    assert ScenarioData.YIELD_TERM_STRUCTURE in scenario.data
    assert scenario.data[ScenarioData.YIELD_TERM_STRUCTURE] == term_structure


if __name__ == "__main__":
    pytest.main([__file__])
