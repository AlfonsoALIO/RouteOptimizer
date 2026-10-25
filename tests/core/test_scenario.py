"""Story 2.1: reject an incomplete mine scenario."""

import pytest

from core.scenario import MineScenario, ScenarioError, load_scenario


def _valid_payload():
    return {
        "locations": [
            {"name": "garage", "resident_capacity": 2},
            {"name": "S1", "resident_capacity": 2},
            {"name": "C", "resident_capacity": 2},
        ],
        "arcs": [
            {"source": "garage", "destination": "S1", "travel_time_minutes": 12.0},
            {"source": "S1", "destination": "C", "travel_time_minutes": 18.0},
            {"source": "C", "destination": "garage", "travel_time_minutes": 15.0},
        ],
        "demands": [
            {"source": "S1", "destination": "C", "tons": 800.0},
        ],
        "trucks": [
            {"name": "truck_1", "tonnage_capacity": 100.0},
            {"name": "truck_2", "tonnage_capacity": 100.0},
        ],
        "shift_length_hours": 12.0,
        "fleet_size": 2,
    }


def test_load_valid_scenario_keeps_fields_and_units():
    scenario = load_scenario(_valid_payload())

    assert isinstance(scenario, MineScenario)
    assert scenario.UNITS["demand"] == "tons"
    assert scenario.UNITS["truck_capacity"] == "tons"
    assert scenario.UNITS["shift_length"] == "hours"
    assert scenario.UNITS["travel_time"] == "minutes"

    assert [loc["name"] for loc in scenario.locations] == ["garage", "S1", "C"]
    assert scenario.arcs[0]["travel_time_minutes"] == 12.0
    assert scenario.demands[0]["tons"] == 800.0
    assert scenario.trucks[0]["tonnage_capacity"] == 100.0
    assert scenario.shift_length_hours == 12.0
    assert scenario.fleet_size == 2


@pytest.mark.parametrize("missing_field", [
    "locations",
    "arcs",
    "demands",
    "trucks",
    "shift_length_hours",
    "fleet_size",
])
def test_missing_required_field_names_the_field(missing_field):
    payload = _valid_payload()
    del payload[missing_field]

    with pytest.raises(ScenarioError, match="missing required field: %s" % missing_field):
        load_scenario(payload)


def test_unknown_location_on_arc_is_rejected():
    payload = _valid_payload()
    payload["arcs"].append(
        {"source": "S1", "destination": "UNKNOWN", "travel_time_minutes": 10.0}
    )

    with pytest.raises(ScenarioError, match="unknown location: UNKNOWN"):
        load_scenario(payload)


def test_unknown_location_on_demand_is_rejected():
    payload = _valid_payload()
    payload["demands"].append(
        {"source": "UNKNOWN", "destination": "C", "tons": 100.0}
    )

    with pytest.raises(ScenarioError, match="unknown location: UNKNOWN"):
        load_scenario(payload)
