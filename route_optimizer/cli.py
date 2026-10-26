"""Command-line entry points: dispatch and shift-plan (no SQL, no network)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from core.batch import default_num_segments, parameters_from_scenario, run_batch
from core.optimization import flow_values, inventory_values
from core.scenario import ScenarioError, load_scenario_file
from core_search.run import run as run_dispatch


def _write_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")


def _dispatch_result_payload(
    solution, scenario, num_segments, num_trucks, stop_reason=None
):
    if stop_reason == "time_limit":
        return {
            "status": "time_limit",
            "optimal": False,
            "stop_reason": "time_limit",
            "num_segments": num_segments,
            "num_trucks": num_trucks,
            "fleet_size": scenario.fleet_size,
        }

    if solution is None:
        return {
            "status": "no_solution",
            "optimal": False,
            "stop_reason": stop_reason or "exhausted",
            "num_segments": num_segments,
            "num_trucks": num_trucks,
            "fleet_size": scenario.fleet_size,
        }

    steps = []
    prev_seg = solution.path_from_root()[0].state.segment
    for ix, node in enumerate(solution.path_from_root()):
        if not node.action:
            continue
        state = node.state
        repeated = state.segment - prev_seg
        prev_seg = state.segment
        steps.append(
            {
                "index": ix,
                "segments": repeated,
                "tons_moved": state.total_covered_demand(),
                "travel_minutes": state.trips,
                "movements": [
                    {
                        "truck": m.truck.name,
                        "source": m.source.name,
                        "destination": m.destination.name,
                    }
                    for m in node.action.movements
                ],
            }
        )

    return {
        "status": "ok",
        "optimal": stop_reason == "optimal" or stop_reason is None,
        "stop_reason": stop_reason or "optimal",
        "cost_minutes": solution.cost,
        "travel_minutes": solution.state.trips,
        "tons_covered": solution.state.total_covered_demand(),
        "num_segments": num_segments,
        "num_trucks": num_trucks,
        "steps": steps,
    }


def _has_numeric_solution(variables):
    """True when pulp assigned numeric values to at least one flow variable."""
    from pulp import value

    for series in variables["flow"].values():
        for var in series:
            if value(var) is not None:
                return True
    return False


def _shift_plan_payload(result):
    proven = bool(getattr(result, "proven_optimal", result.optimal))
    time_limit_reached = bool(getattr(result, "time_limit_reached", False))
    payload = {
        "status": result.status_name,
        "optimal": proven,
        "proven_optimal": proven,
        "time_limit_reached": time_limit_reached,
        "shift_length_hours": result.problem.shift_length_hours,
        "num_segments": result.problem.num_segments,
        "segment_length_minutes": result.problem.segment_length_minutes,
        "truck_capacity": result.problem.truck_capacity,
        "fleet_size": result.problem.fleet_size,
    }
    include_plan = proven or (
        time_limit_reached and _has_numeric_solution(result.variables)
    )
    if include_plan:
        inv = inventory_values(result.variables)
        flows = flow_values(result.variables)
        payload["inventory"] = inv
        payload["flow"] = {
            "%s->%s" % (src, dst): series for (src, dst), series in flows.items()
        }
    return payload


def cmd_dispatch(args):
    """Run A* dispatch on a scenario file and write JSON output."""
    scenario = load_scenario_file(args.scenario)
    num_trucks = args.trucks if args.trucks is not None else scenario.fleet_size
    num_segments = (
        args.segments
        if args.segments is not None
        else default_num_segments(scenario)
    )

    solution = run_dispatch(
        num_segments=num_segments,
        num_trucks=num_trucks,
        scenario=scenario,
        time_limit_seconds=args.time_limit,
    )
    stop_reason = run_dispatch.last_stop_reason
    payload = _dispatch_result_payload(
        solution, scenario, num_segments, num_trucks, stop_reason=stop_reason
    )
    _write_json(args.output, payload)

    if stop_reason == "time_limit":
        print("dispatch: time limit reached", file=sys.stderr)
        return 1
    if solution is None:
        print("dispatch: no solution found", file=sys.stderr)
        return 1
    print("dispatch: wrote %s (cost_minutes=%s)" % (args.output, payload["cost_minutes"]))
    return 0


def cmd_shift_plan(args):
    """Run the mine-wide MILP shift plan and write JSON output."""
    scenario = load_scenario_file(args.scenario)
    num_segments = args.segments
    params = parameters_from_scenario(scenario, num_segments=num_segments)
    result = run_batch(
        scenario,
        params=params,
        persist=False,
        num_segments=num_segments,
        time_limit_seconds=args.time_limit,
    )
    payload = _shift_plan_payload(result)
    _write_json(args.output, payload)

    if getattr(result, "time_limit_reached", False):
        print(
            "shift-plan: time limit reached (status=%s, proven_optimal=%s)"
            % (result.status_name, payload["proven_optimal"]),
            file=sys.stderr,
        )
        return 1
    if not result.optimal:
        print(
            "shift-plan: infeasible (status=%s)" % result.status_name,
            file=sys.stderr,
        )
        return 1
    print(
        "shift-plan: wrote %s (status=%s)" % (args.output, result.status_name)
    )
    return 0


def _add_time_limit_arg(parser):
    parser.add_argument(
        "--time-limit",
        type=float,
        default=None,
        metavar="SECONDS",
        help="Stop the solve after this many seconds (not proven optimal)",
    )


def build_parser():
    parser = argparse.ArgumentParser(
        prog="route-optimizer",
        description="Mine fleet dispatch (A*) and shift plan (MILP) from a scenario file.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    dispatch = sub.add_parser("dispatch", help="Run A* dispatch on a scenario file")
    dispatch.add_argument("scenario", help="Path to scenario JSON file")
    dispatch.add_argument(
        "-o",
        "--output",
        required=True,
        help="Path to write the dispatch JSON result",
    )
    dispatch.add_argument(
        "--segments",
        type=int,
        default=None,
        help="Dispatch horizon in segments (default: from shift / min travel time)",
    )
    dispatch.add_argument(
        "--trucks",
        type=int,
        default=None,
        help="Truck count (default: scenario fleet_size)",
    )
    _add_time_limit_arg(dispatch)
    dispatch.set_defaults(func=cmd_dispatch)

    shift = sub.add_parser("shift-plan", help="Run MILP shift plan on a scenario file")
    shift.add_argument("scenario", help="Path to scenario JSON file")
    shift.add_argument(
        "-o",
        "--output",
        required=True,
        help="Path to write the shift-plan JSON result",
    )
    shift.add_argument(
        "--segments",
        type=int,
        default=None,
        help="Number of segments (default: from shift / min travel time)",
    )
    _add_time_limit_arg(shift)
    shift.set_defaults(func=cmd_shift_plan)

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except ScenarioError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 1
    except ValueError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 1


def dispatch_main(argv=None):
    """Console script: route-optimizer-dispatch."""
    argv = list(sys.argv[1:] if argv is None else argv)
    return main(["dispatch"] + argv)


def shift_plan_main(argv=None):
    """Console script: route-optimizer-shift-plan."""
    argv = list(sys.argv[1:] if argv is None else argv)
    return main(["shift-plan"] + argv)


if __name__ == "__main__":
    sys.exit(main())
