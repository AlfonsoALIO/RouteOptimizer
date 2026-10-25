"""Story 2.5: haul rows become loader-to-destination scenarios."""

import pytest

from core.data_access import build_haul_query
from core.haul_scenario import scenario_from_haul_rows
from core.scenario import ScenarioError


def _caller_kwargs():
    return {
        "demands": [{"source": "C243", "destination": "CRUSHER", "tons": 1000.0}],
        "trucks": [{"name": "truck_1", "tonnage_capacity": 100.0}],
        "resident_capacity": 2,
        "shift_length_hours": 12.0,
        "fleet_size": 5,
    }


def test_haul_rows_become_loader_destination_arcs_with_mean_minutes():
    rows = [
        {
            "loader": "C243",
            "destination": "CRUSHER",
            "haul_time": 10.0,
            "distance": 100.0,
        },
        {
            "loader": "C243",
            "destination": "CRUSHER",
            "haul_time": 20.0,
            "distance": 140.0,
        },
        {
            "loader": "R418",
            "destination": "DUMP",
            "haul_time": 30.0,
            "distance": 200.0,
        },
    ]
    kwargs = _caller_kwargs()
    kwargs["demands"] = [
        {"source": "C243", "destination": "CRUSHER", "tons": 1000.0},
        {"source": "R418", "destination": "DUMP", "tons": 500.0},
    ]

    scenario = scenario_from_haul_rows(rows, **kwargs)

    names = {loc["name"] for loc in scenario.locations}
    assert names == {"C243", "CRUSHER", "R418", "DUMP"}
    assert all(loc["resident_capacity"] == 2 for loc in scenario.locations)

    arcs = {(a["source"], a["destination"]): a for a in scenario.arcs}
    assert arcs[("C243", "CRUSHER")]["travel_time_minutes"] == 15.0
    assert arcs[("C243", "CRUSHER")]["distance"] == 120.0
    assert arcs[("R418", "DUMP")]["travel_time_minutes"] == 30.0


def test_missing_loader_on_row_fails_by_name():
    rows = [
        {"destination": "CRUSHER", "haul_time": 10.0, "distance": 100.0},
    ]
    with pytest.raises(ScenarioError, match="missing required field: loader"):
        scenario_from_haul_rows(rows, **_caller_kwargs())


def test_missing_caller_field_fails_by_name():
    rows = [
        {
            "loader": "C243",
            "destination": "CRUSHER",
            "haul_time": 10.0,
            "distance": 100.0,
        },
    ]
    kwargs = _caller_kwargs()
    kwargs["fleet_size"] = None
    with pytest.raises(ScenarioError, match="missing required field: fleet_size"):
        scenario_from_haul_rows(rows, **kwargs)


def test_unfiltered_query_has_no_hardcoded_loaders():
    sql = build_haul_query(loaders=None)
    assert "C243" not in sql
    assert "R418" not in sql
    assert "R422" not in sql
    assert "R417" not in sql
    assert "Cargco IN" not in sql


def test_filtered_query_includes_only_requested_loaders():
    sql = build_haul_query(loaders=["C243", "R418"])
    assert "Cargco IN ('C243', 'R418')" in sql
    assert "R422" not in sql
    assert "R417" not in sql
