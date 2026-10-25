"""Story 2.4: fleet form edits the mine scenario."""

import json

import django
from django.conf import settings

if not settings.configured:
    settings.configure(
        SECRET_KEY="test-secret-for-fleet-form",
        USE_I18N=False,
        USE_TZ=False,
        FORM_RENDERER="django.forms.renderers.DjangoTemplates",
    )
    django.setup()

from lean_ui.fleet_ui.forms import FleetConfigurationForm


def test_form_initial_from_toy_mine_includes_scenario_fields():
    form = FleetConfigurationForm.from_toy_mine()
    initial = form.initial

    assert "locations_json" in initial
    assert "arcs_json" in initial
    assert "demands_json" in initial
    assert initial["truck_capacity"] == 100
    assert initial["num_segments"] == 58
    assert initial["num_trucks"] == 21

    locations = json.loads(initial["locations_json"])
    names = {loc["name"] for loc in locations}
    assert {"S1", "S2", "L1", "L2", "W", "C", "garage"} <= names

    arcs = json.loads(initial["arcs_json"])
    assert all("travel_time_minutes" in arc for arc in arcs)


def test_valid_edit_builds_scenario_for_dispatcher():
    form = FleetConfigurationForm.from_toy_mine()
    data = {key: form.initial[key] for key in form.fields}
    demands = json.loads(data["demands_json"])
    demands[0]["tons"] = 500.0
    data["demands_json"] = json.dumps(demands)
    data["truck_capacity"] = 80.0
    data["num_trucks"] = 4
    data["fleet_size"] = 4
    data["num_segments"] = 20

    bound = FleetConfigurationForm(data)
    assert bound.is_valid(), bound.errors
    scenario = bound.build_scenario()
    assert scenario.demands[0]["tons"] == 500.0
    assert scenario.trucks[0]["tonnage_capacity"] == 80.0
    assert len(scenario.trucks) == 4


def test_unknown_location_shows_named_error_and_is_invalid():
    form = FleetConfigurationForm.from_toy_mine()
    data = {key: form.initial[key] for key in form.fields}
    arcs = json.loads(data["arcs_json"])
    arcs.append(
        {
            "source": "S1",
            "destination": "NO_SUCH_PLACE",
            "travel_time_minutes": 10.0,
        }
    )
    data["arcs_json"] = json.dumps(arcs)

    bound = FleetConfigurationForm(data)
    assert not bound.is_valid()
    errors = " ".join(str(e) for e in bound.non_field_errors())
    assert "unknown location: NO_SUCH_PLACE" in errors


def test_missing_required_scenario_field_names_the_problem():
    form = FleetConfigurationForm.from_toy_mine()
    data = {key: form.initial[key] for key in form.fields}
    data["locations_json"] = "[]"

    bound = FleetConfigurationForm(data)
    assert not bound.is_valid()
    errors = " ".join(str(e) for e in bound.non_field_errors())
    assert "locations" in errors.lower() or "non-empty" in errors.lower()
