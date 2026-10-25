"""Story 1.3: LinearProblem reads arc endpoints from the travel-time map."""

import math

import pytest

from core.optimization import LinearProblem, solve


def test_locations_are_arc_endpoints_not_keys_method():
    arc_times = {"DST": 60.0}
    problem = LinearProblem(("SRC", "DST"), arc_times, fleet_size=5)

    assert problem.locations == ("SRC", "DST")
    assert not callable(problem.locations)
    assert problem.locations is not arc_times.keys
    assert problem.num_segments == math.ceil(10 * 60 * 2 / 60.0)


def test_formulation_builds_and_iterates_locations():
    problem = LinearProblem(("SRC", "DST"), {"DST": 120.0}, fleet_size=5)

    status, variables = solve(problem)

    assert set(variables.keys()) == set(problem.locations)
    assert status is not None
    for loc in problem.locations:
        assert len(variables[loc]) == problem.num_segments


def test_missing_destination_fails_at_construction():
    with pytest.raises(ValueError, match="missing destination travel time: MISSING"):
        LinearProblem(("SRC", "MISSING"), {"DST": 60.0}, fleet_size=5)
