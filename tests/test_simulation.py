import datetime

import pytest
import QuantLib as ql

from brms.models.bank import Bank
from brms.models.scenario import Scenario, ScenarioBuilder, ScenarioManager
from brms.models.simulation import Simulation
from brms.utils import pydate_to_qldate


@pytest.fixture
def bank():
    return Bank()


@pytest.fixture
def scenario_manager():
    scenario_manager = ScenarioManager()
    day_counter = ql.Actual360()

    for day in range(1, 10):
        date = datetime.date(2023, 1, day)
        scenario_builder = ScenarioBuilder(date)
        interest_rate = 0.05 + day / 1000
        flat_forward = ql.FlatForward(
            pydate_to_qldate(date),
            ql.QuoteHandle(ql.SimpleQuote(interest_rate)),
            day_counter,
        )
        term_structure = ql.YieldTermStructureHandle(flat_forward)
        scenario_builder.with_term_structure(term_structure)
        scenario = scenario_builder.build()
        scenario_manager.add_scenario(date, scenario)

    return scenario_manager


@pytest.fixture
def simulation(bank, scenario_manager):
    return Simulation(bank, scenario_manager)


def test_add_and_set_scenario(simulation, scenario_manager):
    """Test setting the current scenario for the simulation."""
    date = datetime.date(2023, 1, 10)
    scenario = Scenario(date)
    scenario_manager.add_scenario(date, scenario)

    simulation.set_scenario(date)
    assert simulation.current_scenario == scenario


def test_set_scenario_not_found(simulation):
    """Test setting a scenario that does not exist."""
    date = datetime.date(2030, 1, 1)
    with pytest.raises(ValueError, match=f"No scenario found for date: {date}"):
        simulation.set_scenario(date)


def test_run_simulation(simulation, scenario_manager):
    """Test running the simulation."""
    date = datetime.date(2023, 1, 1)
    simulation.set_scenario(date)
    simulation.run()
    assert True


def test_run_simulation_no_scenario(simulation):
    """Test running the simulation without setting a scenario."""
    with pytest.raises(ValueError, match="No scenario is set for the simulation."):
        simulation.run()


def test_reset_simulation(simulation, scenario_manager):
    """Test resetting the simulation state."""
    date = datetime.date(2023, 1, 1)
    scenario = Scenario(date)
    scenario_manager.add_scenario(date, scenario)

    simulation.set_scenario(date)
    simulation.reset()
    assert simulation.current_scenario is None


if __name__ == "__main__":
    pytest.main()
