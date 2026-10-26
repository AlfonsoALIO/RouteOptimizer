"""Batch MILP runner over a MineScenario (one flow for the whole mine)."""

import math

from pulp import LpStatus

from core import Parameters, ProblemResults
from core.optimization import (
    MineFlowProblem,
    is_optimal_status,
    solve_mine_flow,
    status_suggests_time_limit,
)


def segment_count_for_arc(shift_length_hours, travel_time_minutes):
    """ceil(shift length in minutes / arc travel time in minutes)."""
    return int(math.ceil(float(shift_length_hours) * 60.0 / float(travel_time_minutes)))


def default_num_segments(scenario, shift_length_hours=None):
    """Segment count from shift length and the shortest arc travel time."""
    shift = (
        float(shift_length_hours)
        if shift_length_hours is not None
        else float(scenario.shift_length_hours)
    )
    min_travel = min(float(arc["travel_time_minutes"]) for arc in scenario.arcs)
    return segment_count_for_arc(shift, min_travel)


def demand_schedule_from_scenario(scenario, num_segments):
    """Split each scenario demand arc's total tons evenly across segments."""
    schedule = {}
    for demand in scenario.demands:
        key = (demand["source"], demand["destination"])
        total = float(demand["tons"])
        per = total / float(num_segments)
        schedule[key] = [per] * int(num_segments)
    return schedule


def parameters_from_scenario(scenario, num_segments=None):
    """Build Parameters from a scenario (even demand split, scenario shift length)."""
    if num_segments is None:
        num_segments = default_num_segments(scenario)
    return Parameters(
        tonnage_demand=demand_schedule_from_scenario(scenario, num_segments),
        shift_length=scenario.shift_length_hours,
        num_segments=num_segments,
    )


def run_batch(
    scenario,
    params=None,
    job_name="TestJob",
    persist=True,
    num_segments=None,
    time_limit_seconds=None,
):
    """Solve one mine-wide truck-flow model for the scenario.

    ``params`` supplies shift length and per-arc/segment tonnage demand.
    When omitted, parameters are derived from the scenario.

    Returns a single ProblemResults for the whole mine (not one per arc).
    Infeasible runs report status and are not persisted as a success.
    With ``time_limit_seconds``, a stopped solve is not marked proven optimal.
    """
    if params is None:
        params = parameters_from_scenario(scenario, num_segments=num_segments)
    elif not isinstance(params, Parameters):
        raise ValueError("missing required field: parameters")

    problem = MineFlowProblem.from_scenario(
        scenario, params=params, num_segments=num_segments
    )
    status, variables = solve_mine_flow(
        problem, time_limit_seconds=time_limit_seconds
    )
    result = ProblemResults(status, variables)
    result.problem = problem
    result.status_name = LpStatus[status]
    result.proven_optimal = is_optimal_status(status)
    result.optimal = result.proven_optimal
    result.time_limit_reached = status_suggests_time_limit(
        status, time_limit_seconds
    )

    if persist and result.proven_optimal:
        import core.data_access as da

        da.persist_results(job_name, {"mine_flow": result})

    return result
