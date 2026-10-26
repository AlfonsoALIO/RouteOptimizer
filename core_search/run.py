"""Dispatch runner for the named toy-mine scenario fixture."""

import math
import pprint

from core.fixtures import load_toy_mine
from core_search.scenario_bridge import fleet_state_from_scenario
from core_search.search import AStar


def _heuristic(state):
    """A* heuristic: remaining haul work in minutes (not trip count).

    For each open demand arc, estimate how many truck-dispatches are still
    needed and multiply by that arc's travel time.
    """
    trucks = sorted(state.trucks, key=lambda t: t.tonnage_capacity, reverse=True)

    routes = list()
    for k, v in state.route_demands.items():
        remaining = v - state.covered_demands[k]
        if remaining > 0:
            routes.append((k, remaining))

    routes = sorted(routes, key=lambda r: r[1], reverse=True)

    minutes_remaining = 0.0

    for k, remaining in routes:
        location_capacity = k[1].resident_capacity
        to_take = location_capacity if len(trucks) >= location_capacity else len(trucks)
        taken_trucks = trucks[:to_take]
        trucks = trucks[to_take:]

        if to_take != 0:
            capacity = sum(t.tonnage_capacity for t in taken_trucks)
            segments = math.ceil(float(remaining) / capacity)
            arc_minutes = state.config.travel_time(k[0], k[1])
            minutes_remaining += segments * len(taken_trucks) * arc_minutes

    return minutes_remaining


def run(
    num_segments=58,
    num_trucks=21,
    listener=None,
    scenario=None,
    time_limit_seconds=None,
):
    """Run the dispatcher on a scenario (defaults to the toy-mine fixture).

    Optional ``time_limit_seconds`` stops the search early. The stop reason is
    available as ``run.last_stop_reason`` (``optimal``, ``exhausted``, or
    ``time_limit``).
    """
    if scenario is None:
        scenario = load_toy_mine()

    initial_state = fleet_state_from_scenario(scenario, num_segments, num_trucks)
    searcher = AStar(
        initial_state,
        _heuristic,
        listener,
        time_limit_seconds=time_limit_seconds,
    )
    solution = searcher.solve()
    run.last_stop_reason = searcher.stop_reason
    return solution


run.last_stop_reason = None


if __name__ == "__main__":
    solution = run(
        listener=lambda t: print(
            "Iteration: %i\tEstimated Cost: %s\tActual Cost: %s\tSegment: %i\tProgress: %i tons"
            % t
        )
    )

    if solution:
        print()
        print("Total travel time: %s minutes" % solution.cost)
        print()
        nodes = solution.path_from_root()
        prev_seg = 1
        for ix, n in enumerate(nodes):
            if n.action:
                s = n.state
                num_segments = s.segment - prev_seg
                prev_seg = s.segment
                print(
                    "Dispatch: %i\tRepeated: %i times\tTons moved: %i"
                    % (ix, num_segments, s.total_covered_demand())
                )
                pprint.pprint(n.action.movements)
                print()
    else:
        print("No solution found")
