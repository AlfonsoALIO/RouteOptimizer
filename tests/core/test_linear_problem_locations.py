"""Story 1.3: LinearProblem reads arc endpoints from the travel-time map."""

import math

import pytest

from core.optimization import LinearProblem, solve


def test_locations_are_arc_endpoints():
    problem = LinearProblem(
        ("SRC", "DST"),
        fleet_size=5,
        travel_time_minutes=60.0,
        shift_length_hours=10.0,
    )

    assert problem.locations == ("SRC", "DST")
    assert not callable(problem.locations)
    assert problem.num_segments == math.ceil(10.0 * 60.0 / 60.0)


def test_formulation_builds_and_iterates_locations():
    problem = LinearProblem(
        ("SRC", "DST"),
        fleet_size=5,
        travel_time_minutes=120.0,
        shift_length_hours=10.0,
    )

    status, variables = solve(problem)

    assert set(variables.keys()) == set(problem.locations)
    assert status is not None
    for loc in problem.locations:
        assert len(variables[loc]) == problem.num_segments


def test_non_positive_travel_time_fails_at_construction():
    with pytest.raises(ValueError, match="travel_time_minutes must be positive"):
        LinearProblem(
            ("SRC", "DST"),
            fleet_size=5,
            travel_time_minutes=0,
            shift_length_hours=10.0,
        )
