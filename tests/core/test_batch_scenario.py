"""Story 2.3: batch job runs on the same scenario as the dispatcher."""

import math
from pathlib import Path

from core.batch import run_batch, segment_count_for_arc
from core.fixtures import load_toy_mine
from core.optimization import LinearProblem


def test_segment_count_uses_shift_minutes_over_travel_time():
    assert segment_count_for_arc(12.0, 15.0) == math.ceil(12.0 * 60.0 / 15.0)


def test_batch_runs_on_toy_mine_without_sql():
    scenario = load_toy_mine()
    results = run_batch(scenario, job_name="toy_batch", persist=False)

    assert len(results) == len(scenario.arcs)
    assert set(results.keys()) == {
        (arc["source"], arc["destination"]) for arc in scenario.arcs
    }
    for result in results.values():
        assert result.status is not None

    # Fleet size and shift come from scenario (not literals 29 / 10h / 2 shifts)
    assert scenario.fleet_size == 21
    assert scenario.shift_length_hours == 12.0


def test_batch_subproblem_segment_count_matches_formula():
    scenario = load_toy_mine()
    arc = scenario.arcs[0]
    problem = LinearProblem(
        (arc["source"], arc["destination"]),
        scenario.fleet_size,
        arc["travel_time_minutes"],
        scenario.shift_length_hours,
    )
    assert problem.num_segments == segment_count_for_arc(
        scenario.shift_length_hours, arc["travel_time_minutes"]
    )
    assert problem.fleet_size == scenario.fleet_size


def test_dispatcher_form_still_exposes_segment_and_truck_counts():
    forms_path = Path(__file__).resolve().parents[2] / "lean_ui" / "fleet_ui" / "forms.py"
    source = forms_path.read_text()
    assert "num_segments" in source
    assert "num_trucks" in source
