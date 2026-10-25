"""Story 5.1: one flow model over the whole mine."""

import math

from pulp import LpStatus

from core.batch import parameters_from_scenario, run_batch
from core.fixtures import load_toy_mine
from core.optimization import (
    MineFlowProblem,
    flow_values,
    inventory_values,
    solve_mine_flow,
)
from core.scenario import load_scenario


def _tiny_feasible_scenario():
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
            "demands": [{"source": "S", "destination": "C", "tons": 100.0}],
            "trucks": [
                {"name": "truck_1", "tonnage_capacity": 100.0},
                {"name": "truck_2", "tonnage_capacity": 100.0},
            ],
            "shift_length_hours": 1.0,
            "fleet_size": 2,
        }
    )


def _infeasible_scenario():
    return load_scenario(
        {
            "locations": [
                {"name": "garage", "resident_capacity": 1},
                {"name": "S", "resident_capacity": 1},
            ],
            "arcs": [
                {"source": "garage", "destination": "S", "travel_time_minutes": 30.0},
                {"source": "S", "destination": "garage", "travel_time_minutes": 30.0},
            ],
            "demands": [],
            "trucks": [
                {"name": "truck_%i" % i, "tonnage_capacity": 100.0} for i in range(1, 6)
            ],
            "shift_length_hours": 1.0,
            "fleet_size": 5,
        }
    )


def test_mine_flow_uses_scenario_arc_endpoints():
    scenario = _tiny_feasible_scenario()
    params = parameters_from_scenario(scenario, num_segments=4)
    problem = MineFlowProblem.from_scenario(scenario, params=params)

    assert set(problem.locations) == {"garage", "S", "C"}
    assert ("garage", "S") in {(s, d) for s, d, _ in problem.arcs}
    assert problem.num_segments == 4
    assert problem.fleet_size == 2


def test_known_feasible_fixture_solves_with_conservation():
    scenario = _tiny_feasible_scenario()
    result = run_batch(scenario, persist=False, num_segments=4)

    assert result.optimal
    assert LpStatus[result.status] == "Optimal"

    problem = result.problem
    inv = inventory_values(result.variables)
    flows = flow_values(result.variables)

    # Arc endpoints in the solution come from the scenario
    assert set(flows.keys()) == {(a["source"], a["destination"]) for a in scenario.arcs}

    for t in range(problem.num_segments):
        # Fleet size: trucks used on arcs this segment
        assert sum(flows[arc][t] for arc in flows) <= problem.fleet_size

        for loc in problem.locations:
            assert inv[loc][t] <= problem.resident_capacities[loc]
            assert inv[loc][t + 1] <= problem.resident_capacities[loc]

            outgoing = sum(
                flows[arc][t] for arc in flows if arc[0] == loc
            )
            assert outgoing <= inv[loc][t]

            incoming = 0
            for arc, series in flows.items():
                if arc[1] != loc:
                    continue
                duration = problem.arc_duration[arc]
                depart_t = t - duration + 1
                if depart_t >= 0:
                    incoming += series[depart_t]

            assert inv[loc][t + 1] == inv[loc][t] - outgoing + incoming

        assert sum(inv[loc][0] for loc in problem.locations) == problem.fleet_size


def test_batch_does_not_solve_separate_model_per_arc():
    scenario = _tiny_feasible_scenario()
    result = run_batch(scenario, persist=False, num_segments=4)

    # One result object for the mine, not a per-arc map
    assert hasattr(result, "status")
    assert "inventory" in result.variables
    assert "flow" in result.variables
    assert not isinstance(result, dict)


def test_infeasible_scenario_reports_status_and_skips_success_persist(tmp_path, monkeypatch):
    scenario = _infeasible_scenario()
    # Sum of capacities (1+1) < fleet_size 5
    assert sum(loc["resident_capacity"] for loc in scenario.locations) < scenario.fleet_size

    persisted = []

    def fake_persist(job_name, problem_results):
        persisted.append((job_name, problem_results))

    monkeypatch.setattr("core.data_access.persist_results", fake_persist)

    result = run_batch(scenario, job_name=str(tmp_path / "fail_job"), persist=True)

    assert not result.optimal
    assert LpStatus[result.status] == "Infeasible"
    assert persisted == []


def test_toy_mine_flow_builds_and_solves():
    scenario = load_toy_mine()
    params = parameters_from_scenario(scenario)
    problem = MineFlowProblem.from_scenario(scenario, params=params)
    assert problem.num_segments == math.ceil(12.0 * 60.0 / 15.0)
    assert problem.truck_capacity == 100.0

    status, variables = solve_mine_flow(problem)
    assert LpStatus[status] in ("Optimal", "Infeasible")
    if LpStatus[status] == "Optimal":
        inv = inventory_values(variables)
        assert sum(inv[loc][0] for loc in inv) == scenario.fleet_size
