"""Batch MILP runner over a MineScenario (one subproblem per directed arc)."""

import math

from core import ProblemResults
from core.optimization import LinearProblem, solve


def segment_count_for_arc(shift_length_hours, travel_time_minutes):
    """ceil(shift length in minutes / arc travel time in minutes)."""
    return int(math.ceil(float(shift_length_hours) * 60.0 / float(travel_time_minutes)))


def run_batch(scenario, job_name="TestJob", persist=True):
    """Solve one LinearProblem per directed arc in the scenario.

    Fleet size and shift length come from the scenario. The current per-arc
    tonnage constraint (demand 1, capacity 100) is unchanged.
    """
    results = {}
    for arc in scenario.arcs:
        name = (arc["source"], arc["destination"])
        problem = LinearProblem(
            name,
            scenario.fleet_size,
            arc["travel_time_minutes"],
            scenario.shift_length_hours,
        )
        status, variables = solve(problem)
        results[name] = ProblemResults(status, variables)

    if persist:
        import core.data_access as da

        da.persist_results(job_name, results)

    return results
