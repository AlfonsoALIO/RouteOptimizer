"""Story 2.3 / 5.1: batch job runs on the same scenario as the dispatcher."""

import math
from pathlib import Path

from core.batch import parameters_from_scenario, run_batch, segment_count_for_arc
from core.fixtures import load_toy_mine
from core.optimization import LinearProblem, MineFlowProblem


def test_segment_count_uses_shift_minutes_over_travel_time():
    assert segment_count_for_arc(12.0, 15.0) == math.ceil(12.0 * 60.0 / 15.0)


def test_batch_runs_on_toy_mine_without_sql():
    scenario = load_toy_mine()
    result = run_batch(scenario, job_name="toy_batch", persist=False)

    assert result.status is not None
    assert "inventory" in result.variables
    assert "flow" in result.variables

    # Fleet size and shift come from scenario / Parameters (not literals 29 / 10h)
    assert scenario.fleet_size == 21
    assert scenario.shift_length_hours == 12.0
    assert result.problem.fleet_size == scenario.fleet_size
    assert result.problem.shift_length_hours == scenario.shift_length_hours
    assert result.problem.truck_capacity == 100.0


def test_batch_subproblem_segment_count_matches_formula():
    scenario = load_toy_mine()
    arc = scenario.arcs[0]
    nseg = segment_count_for_arc(
        scenario.shift_length_hours, arc["travel_time_minutes"]
    )
    problem = LinearProblem(
        (arc["source"], arc["destination"]),
        scenario.fleet_size,
        arc["travel_time_minutes"],
        scenario.shift_length_hours,
        truck_capacity=scenario.trucks[0]["tonnage_capacity"],
        segment_demand=[0.0] * nseg,
    )
    assert problem.num_segments == nseg
    assert problem.fleet_size == scenario.fleet_size

    params = parameters_from_scenario(scenario)
    flow = MineFlowProblem.from_scenario(scenario, params=params)
    assert flow.num_segments == segment_count_for_arc(
        scenario.shift_length_hours,
        min(a["travel_time_minutes"] for a in scenario.arcs),
    )


def test_dispatcher_form_still_exposes_segment_and_truck_counts():
    forms_path = Path(__file__).resolve().parents[2] / "lean_ui" / "fleet_ui" / "forms.py"
    source = forms_path.read_text()
    assert "num_segments" in source
    assert "num_trucks" in source
