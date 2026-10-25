"""MILP fleet optimization: per-arc subproblems and whole-mine flow."""

import math
import itertools as it
from collections import defaultdict

from pulp import (
    LpAffineExpression,
    LpConstraint,
    LpConstraintEQ,
    LpConstraintLE,
    LpInteger,
    LpMinimize,
    LpProblem,
    LpStatus,
    LpVariable,
    PULP_CBC_CMD,
    value,
)


class LinearProblem(object):
    """Represents an instance of a subproblem to be solved by the fleet optimizator"""

    def __init__(
        self,
        name,
        fleet_size,
        travel_time_minutes,
        shift_length_hours,
        truck_capacity,
        segment_demand,
    ):
        """Constructor.

        name: (source, destination) arc endpoints
        fleet_size: maximum trucks available in a segment
        travel_time_minutes: travel time for this arc
        shift_length_hours: scenario shift length; segment count is
            ceil(shift_length_hours * 60 / travel_time_minutes)
        truck_capacity: tons per truck (from the scenario)
        segment_demand: tons required on this arc in each segment
        """
        self.name = name
        self.fleet_size = fleet_size
        self.travel_time_minutes = float(travel_time_minutes)
        self.shift_length_hours = float(shift_length_hours)
        self.truck_capacity = float(truck_capacity)
        self.segment_demand = [float(x) for x in segment_demand]

        if not isinstance(name, (tuple, list)) or len(name) != 2:
            raise ValueError("arc name must be a (source, destination) pair, got %r" % (name,))

        source, destination = name
        self.locations = (source, destination)

        if self.travel_time_minutes <= 0:
            raise ValueError(
                "travel_time_minutes must be positive for destination %s" % (destination,)
            )
        if self.shift_length_hours <= 0:
            raise ValueError("shift_length_hours must be positive")
        if self.truck_capacity <= 0:
            raise ValueError("truck_capacity must be positive")

        self.num_segments = int(
            math.ceil(self.shift_length_hours * 60.0 / self.travel_time_minutes)
        )
        if len(self.segment_demand) != self.num_segments:
            raise ValueError(
                "segment_demand length %i must match num_segments %i"
                % (len(self.segment_demand), self.num_segments)
            )


def solve(problem):
    """Core of the fleet optimization algorithm. Runs the MLP for the particular subproblem
    Returns the assignment and the optimized target
    """

    # Instance of the problem
    instance = LpProblem("Fleet Optimizer", LpMinimize)

    # Variables keyed by arc endpoints (locations)
    X = dict()
    for i in problem.locations:
        X[i] = list()
        for j in range(problem.num_segments):
            x = LpVariable("X_%s_%i" % (i, j), lowBound=0, cat=LpInteger)
            X[i].append(x)

    # The target function
    target = LpAffineExpression([(x, 1) for x in it.chain.from_iterable(X.values())])
    instance += target

    capacity = problem.truck_capacity
    for i in problem.locations:
        for j in range(problem.num_segments):
            instance += capacity * X[i][j] >= problem.segment_demand[j]

    # Fleet size
    for j in range(problem.num_segments):
        elements = [(X[i][j], 1) for i in problem.locations]
        expr = LpAffineExpression(elements)
        instance += LpConstraint(
            expr, LpConstraintLE, "Fleet_conservation_%i" % j, problem.fleet_size
        )

    status = instance.solve(PULP_CBC_CMD(msg=0))
    return status, X


def _normalize_arc_key(key):
    if isinstance(key, (tuple, list)) and len(key) == 2:
        return (key[0], key[1])
    raise ValueError("demand arc key must be a (source, destination) pair, got %r" % (key,))


def normalize_tonnage_demand(tonnage_demand, num_segments):
    """Normalize Parameters.tonnage_demand to {(src, dst): [tons per segment]}."""
    if tonnage_demand is None:
        raise ValueError("missing required field: tonnage_demand")
    if not isinstance(tonnage_demand, dict):
        raise ValueError(
            "tonnage_demand must map each arc to a per-segment list of tons"
        )

    schedule = {}
    for key, val in tonnage_demand.items():
        arc = _normalize_arc_key(key)
        if not isinstance(val, (list, tuple)):
            raise ValueError(
                "tonnage_demand for %s must be a per-segment list, got %r" % (arc, val)
            )
        if len(val) != num_segments:
            raise ValueError(
                "tonnage_demand for %s has %i segments, expected %i"
                % (arc, len(val), num_segments)
            )
        schedule[arc] = [float(x) for x in val]
    return schedule


class MineFlowProblem(object):
    """One truck-flow model over all scenario arcs and a shared segment horizon."""

    def __init__(
        self,
        locations,
        arcs,
        resident_capacities,
        fleet_size,
        shift_length_hours,
        truck_capacity,
        tonnage_demand,
        num_segments,
    ):
        """
        locations: iterable of location name strings
        arcs: iterable of dicts with source, destination, travel_time_minutes
        resident_capacities: map location name -> capacity
        truck_capacity: tons per truck from the scenario
        tonnage_demand: {(src, dst): [tons per segment]}
        num_segments: shared horizon length (scenario segment count)
        """
        self.locations = tuple(sorted(locations))
        self.arcs = tuple(
            (
                arc["source"],
                arc["destination"],
                float(arc["travel_time_minutes"]),
            )
            for arc in arcs
        )
        self.resident_capacities = dict(resident_capacities)
        self.fleet_size = int(fleet_size)
        self.shift_length_hours = float(shift_length_hours)
        self.truck_capacity = float(truck_capacity)
        self.num_segments = int(num_segments)

        if self.fleet_size <= 0:
            raise ValueError("fleet_size must be positive")
        if self.shift_length_hours <= 0:
            raise ValueError("shift_length_hours must be positive")
        if self.truck_capacity <= 0:
            raise ValueError("truck_capacity must be positive")
        if self.num_segments <= 0:
            raise ValueError("num_segments must be positive")
        if not self.arcs:
            raise ValueError("arcs must be non-empty")
        for src, dst, travel in self.arcs:
            if travel <= 0:
                raise ValueError(
                    "travel_time_minutes must be positive for %s -> %s" % (src, dst)
                )
            if src not in self.resident_capacities or dst not in self.resident_capacities:
                raise ValueError("arc endpoints must appear in resident_capacities")

        self.segment_length_minutes = (
            self.shift_length_hours * 60.0 / float(self.num_segments)
        )
        self.arc_duration = {
            (src, dst): max(1, int(math.ceil(travel / self.segment_length_minutes)))
            for src, dst, travel in self.arcs
        }
        self.tonnage_demand = normalize_tonnage_demand(tonnage_demand, self.num_segments)
        arc_set = {(src, dst) for src, dst, _ in self.arcs}
        for arc in self.tonnage_demand:
            if arc not in arc_set:
                raise ValueError("demand arc %s is not in the scenario arcs" % (arc,))

    @classmethod
    def from_scenario(cls, scenario, params, num_segments=None):
        if params is None:
            raise ValueError("missing required field: parameters")
        if getattr(params, "tonnage_demand", None) is None:
            raise ValueError("missing required field: tonnage_demand")
        if getattr(params, "shift_length", None) is None:
            raise ValueError("missing required field: shift_length")

        if num_segments is None:
            num_segments = params.num_segments
        if num_segments is None:
            min_travel = min(float(a["travel_time_minutes"]) for a in scenario.arcs)
            num_segments = int(
                math.ceil(float(params.shift_length) * 60.0 / min_travel)
            )

        if not scenario.trucks:
            raise ValueError("missing required field: trucks")
        truck_capacity = float(scenario.trucks[0]["tonnage_capacity"])

        capacities = {
            loc["name"]: int(loc["resident_capacity"]) for loc in scenario.locations
        }
        return cls(
            locations=[loc["name"] for loc in scenario.locations],
            arcs=scenario.arcs,
            resident_capacities=capacities,
            fleet_size=scenario.fleet_size,
            shift_length_hours=params.shift_length,
            truck_capacity=truck_capacity,
            tonnage_demand=params.tonnage_demand,
            num_segments=num_segments,
        )


def solve_mine_flow(problem):
    """Solve the whole-mine flow. Returns (status, variables).

    variables keys:
      inventory: loc -> list of LpVariable for t = 0..num_segments
      flow: (src, dst) -> list of LpVariable for departures at t = 0..num_segments-1
    """
    instance = LpProblem("Mine_Flow", LpMinimize)

    locations = problem.locations
    arcs = [(src, dst) for src, dst, _ in problem.arcs]
    T = problem.num_segments
    fleet = problem.fleet_size

    inventory = {
        loc: [
            LpVariable("inv_%s_%i" % (loc, t), lowBound=0, cat=LpInteger)
            for t in range(T + 1)
        ]
        for loc in locations
    }
    flow = {
        arc: [
            LpVariable("flow_%s_%s_%i" % (arc[0], arc[1], t), lowBound=0, cat=LpInteger)
            for t in range(T)
        ]
        for arc in arcs
    }

    outgoing = defaultdict(list)
    incoming = defaultdict(list)
    for src, dst in arcs:
        outgoing[src].append((src, dst))
        incoming[dst].append((src, dst))

    # Objective: minimize truck-movements (feasibility still primary)
    instance += LpAffineExpression(
        [(flow[arc][t], 1) for arc in arcs for t in range(T)]
    )

    # Initial placement: all trucks somewhere, within capacity
    instance += LpConstraint(
        LpAffineExpression([(inventory[loc][0], 1) for loc in locations]),
        LpConstraintEQ,
        "initial_fleet",
        fleet,
    )
    for loc in locations:
        instance += inventory[loc][0] <= problem.resident_capacities[loc]

    capacity = problem.truck_capacity

    for t in range(T):
        # Per-arc segment demand in tons: capacity * trucks >= tons
        for arc, tons_by_segment in problem.tonnage_demand.items():
            tons = tons_by_segment[t]
            if tons > 0:
                instance += capacity * flow[arc][t] >= tons

        # Departures cannot exceed trucks present
        for loc in locations:
            if outgoing[loc]:
                instance += LpConstraint(
                    LpAffineExpression(
                        [(flow[arc][t], 1) for arc in outgoing[loc]]
                        + [(inventory[loc][t], -1)]
                    ),
                    LpConstraintLE,
                    "depart_%s_%i" % (loc, t),
                    0,
                )

        # Conservation into the next inventory snapshot
        for loc in locations:
            expr_terms = [(inventory[loc][t], 1), (inventory[loc][t + 1], -1)]
            for arc in outgoing[loc]:
                expr_terms.append((flow[arc][t], -1))
            for arc in incoming[loc]:
                duration = problem.arc_duration[arc]
                depart_t = t - duration + 1
                if depart_t >= 0:
                    expr_terms.append((flow[arc][depart_t], 1))
            instance += LpConstraint(
                LpAffineExpression(expr_terms),
                LpConstraintEQ,
                "conserv_%s_%i" % (loc, t),
                0,
            )

            instance += inventory[loc][t + 1] <= problem.resident_capacities[loc]

        # Trucks in use this segment (departures) cannot exceed fleet size
        instance += LpConstraint(
            LpAffineExpression([(flow[arc][t], 1) for arc in arcs]),
            LpConstraintLE,
            "fleet_use_%i" % t,
            fleet,
        )

        # Global truck conservation: residents + still-in-transit == fleet
        # In-transit after movements at t: departed earlier, not yet arrived at t+1
        transit_terms = []
        for arc in arcs:
            duration = problem.arc_duration[arc]
            for age in range(1, duration):
                depart_t = t - age + 1
                if depart_t >= 0:
                    transit_terms.append((flow[arc][depart_t], 1))
        instance += LpConstraint(
            LpAffineExpression(
                [(inventory[loc][t + 1], 1) for loc in locations] + transit_terms
            ),
            LpConstraintEQ,
            "fleet_balance_%i" % t,
            fleet,
        )

    status = instance.solve(PULP_CBC_CMD(msg=0))
    variables = {"inventory": inventory, "flow": flow}
    return status, variables


def inventory_values(variables):
    """Return loc -> list of solved inventory integers."""
    return {
        loc: [int(round(value(var) or 0)) for var in series]
        for loc, series in variables["inventory"].items()
    }


def flow_values(variables):
    """Return (src, dst) -> list of solved departure integers."""
    return {
        arc: [int(round(value(var) or 0)) for var in series]
        for arc, series in variables["flow"].items()
    }


def is_optimal_status(status):
    return LpStatus[status] == "Optimal"
