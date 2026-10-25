"""Story 5.2: shift length and per-segment demand drive the flow."""

import pytest
from pulp import LpStatus

from core import Parameters
from core.batch import parameters_from_scenario, run_batch
from core.optimization import MineFlowProblem, flow_values
from core.scenario import load_scenario


def _scenario(truck_capacity=100.0, fleet_size=2):
    return load_scenario(
        {
            "locations": [
                {"name": "garage", "resident_capacity": 4},
                {"name": "S", "resident_capacity": 2},
                {"name": "C", "resident_capacity": 2},
            ],
            "arcs": [
                {"source": "garage", "destination": "S", "travel_time_minutes": 15.0},
                {"source": "S", "destination": "garage", "travel_time_minutes": 15.0},
                {"source": "S", "destination": "C", "travel_time_minutes": 15.0},
                {"source": "C", "destination": "S", "travel_time_minutes": 15.0},
                {"source": "C", "destination": "garage", "travel_time_minutes": 15.0},
            ],
            "demands": [{"source": "S", "destination": "C", "tons": 200.0}],
            "trucks": [
                {"name": "truck_%i" % i, "tonnage_capacity": truck_capacity}
                for i in range(1, fleet_size + 1)
            ],
            "shift_length_hours": 2.0,
            "fleet_size": fleet_size,
        }
    )


def test_missing_tonnage_demand_names_the_field():
    with pytest.raises(ValueError, match="missing required field: tonnage_demand"):
        Parameters(tonnage_demand=None, shift_length=12.0)


def test_missing_shift_length_names_the_field():
    with pytest.raises(ValueError, match="missing required field: shift_length"):
        Parameters(tonnage_demand={("S", "C"): [1.0]}, shift_length=None)


def test_model_reads_parameters_shift_and_segment_length():
    scenario = _scenario()
    params = Parameters(
        tonnage_demand={("S", "C"): [0.0, 50.0, 100.0, 50.0]},
        shift_length=2.0,
        num_segments=4,
    )
    problem = MineFlowProblem.from_scenario(scenario, params=params)

    assert problem.shift_length_hours == 2.0
    assert problem.num_segments == 4
    assert problem.segment_length_minutes == pytest.approx(2.0 * 60.0 / 4)
    assert problem.truck_capacity == 100.0
    assert problem.tonnage_demand[("S", "C")] == [0.0, 50.0, 100.0, 50.0]


def test_demand_differs_by_segment_and_uses_scenario_capacity():
    scenario = _scenario(truck_capacity=50.0, fleet_size=3)
    demand = {("S", "C"): [0.0, 50.0, 100.0, 50.0]}
    params = Parameters(tonnage_demand=demand, shift_length=2.0, num_segments=4)

    result = run_batch(scenario, params=params, persist=False)

    assert result.optimal
    assert result.problem.truck_capacity == 50.0
    flows = flow_values(result.variables)
    # capacity * trucks >= tons each segment
    for t, tons in enumerate(demand[("S", "C")]):
        assert 50.0 * flows[("S", "C")][t] >= tons - 1e-6


def test_uncoverable_demand_is_infeasible():
    scenario = _scenario(truck_capacity=100.0, fleet_size=1)
    # 500 tons in one segment with one 100-ton truck is impossible
    params = Parameters(
        tonnage_demand={("S", "C"): [500.0, 0.0, 0.0, 0.0]},
        shift_length=2.0,
        num_segments=4,
    )

    result = run_batch(scenario, params=params, persist=False)

    assert not result.optimal
    assert LpStatus[result.status] == "Infeasible"


def test_parameters_from_scenario_splits_totals():
    scenario = _scenario()
    params = parameters_from_scenario(scenario, num_segments=4)
    assert params.shift_length == 2.0
    assert params.num_segments == 4
    assert params.tonnage_demand[("S", "C")] == [50.0, 50.0, 50.0, 50.0]
