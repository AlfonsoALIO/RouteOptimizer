"""Story 6.4: stop long solves at a time limit."""

import json
from pathlib import Path

from core.batch import run_batch
from core.scenario import load_scenario_file
from core_search.run import run as run_dispatch
from route_optimizer import cli

ROOT = Path(__file__).resolve().parents[1]
TINY = ROOT / "samples" / "tiny_feasible.json"
TOY = ROOT / "samples" / "toy_mine.json"


def test_astar_stops_at_zero_time_limit():
    scenario = load_scenario_file(TOY)
    solution = run_dispatch(
        num_segments=58,
        num_trucks=21,
        scenario=scenario,
        time_limit_seconds=0,
    )
    assert solution is None
    assert run_dispatch.last_stop_reason == "time_limit"


def test_astar_without_time_limit_still_solves_tiny():
    scenario = load_scenario_file(TINY)
    solution = run_dispatch(
        num_segments=8,
        num_trucks=2,
        scenario=scenario,
        time_limit_seconds=None,
    )
    assert solution is not None
    assert run_dispatch.last_stop_reason == "optimal"


def test_milp_stops_at_zero_time_limit():
    scenario = load_scenario_file(TINY)
    result = run_batch(
        scenario,
        persist=False,
        num_segments=40,
        time_limit_seconds=0.0,
    )
    assert result.time_limit_reached is True
    assert result.proven_optimal is False
    assert result.optimal is False
    assert result.status_name != "Optimal"


def test_milp_without_time_limit_still_optimal():
    scenario = load_scenario_file(TINY)
    result = run_batch(scenario, persist=False, num_segments=4)
    assert result.proven_optimal is True
    assert result.time_limit_reached is False
    assert result.status_name == "Optimal"


def test_cli_dispatch_time_limit_reports_status(tmp_path):
    out = tmp_path / "dispatch.json"
    code = cli.main(
        [
            "dispatch",
            str(TOY),
            "-o",
            str(out),
            "--segments",
            "58",
            "--trucks",
            "21",
            "--time-limit",
            "0",
        ]
    )
    assert code != 0
    payload = json.loads(out.read_text())
    assert payload["status"] == "time_limit"
    assert payload["optimal"] is False
    assert payload["stop_reason"] == "time_limit"


def test_cli_shift_plan_time_limit_not_proven_optimal(tmp_path):
    out = tmp_path / "plan.json"
    code = cli.main(
        [
            "shift-plan",
            str(TINY),
            "-o",
            str(out),
            "--segments",
            "40",
            "--time-limit",
            "0",
        ]
    )
    assert code != 0
    payload = json.loads(out.read_text())
    assert payload["proven_optimal"] is False
    assert payload["optimal"] is False
    assert payload["time_limit_reached"] is True
    assert payload["status"] != "Optimal"
