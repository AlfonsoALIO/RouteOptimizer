"""Story 4.2: fleet screen submits mine changes with the current fleet."""

import json

import django
from django.conf import settings

if not settings.configured:
    settings.configure(
        SECRET_KEY="test-secret-for-fleet-replan",
        USE_I18N=False,
        USE_TZ=False,
        FORM_RENDERER="django.forms.renderers.DjangoTemplates",
    )
    django.setup()

from lean_ui.fleet_ui.forms import FleetConfigurationForm
from lean_ui.fleet_ui.views import _run_from_form


def _replan_form_data(**overrides):
    form = FleetConfigurationForm.from_toy_mine()
    data = {key: form.initial[key] for key in form.fields}
    # Small fleet for a fast replan window
    data["num_trucks"] = 2
    data["fleet_size"] = 2
    data["num_segments"] = 20
    data["plan_mode"] = "replan"
    data["replan_k"] = 3
    data["current_fleet_json"] = json.dumps(
        {
            "segment": 4,
            "residents": {"S1": ["truck_1"], "garage": ["truck_2"]},
            "in_transit": [],
        }
    )
    data.update(overrides)
    # Choice/float fields may be None in initial
    for key, value in list(data.items()):
        if value is None:
            data[key] = ""
    return data


def test_fleet_screen_replan_close_shovel_returns_plan():
    data = _replan_form_data(
        change_type="close_shovel",
        change_location="S2",
        current_fleet_json=json.dumps(
            {
                "segment": 4,
                "residents": {"S1": ["truck_1"]},
                "in_transit": [
                    {
                        "truck": "truck_2",
                        "source": "garage",
                        "destination": "S1",
                        "remaining_minutes": 20,
                    }
                ],
            }
        ),
    )

    bound = FleetConfigurationForm(data)
    assert bound.is_valid(), bound.errors
    steps = []
    simulation = _run_from_form(bound, steps)
    assert simulation is not None
    assert any("Dispatch:" in s or "Total travel time" in s for s in _formatted(simulation, steps))


def test_fleet_screen_replan_full_queue_returns_plan():
    data = _replan_form_data(
        change_type="full_queue",
        change_location="S1",
        current_fleet_json=json.dumps(
            {
                "segment": 3,
                "residents": {"S1": ["truck_1", "truck_2"]},
                "in_transit": [],
            }
        ),
    )
    bound = FleetConfigurationForm(data)
    assert bound.is_valid(), bound.errors
    steps = []
    simulation = _run_from_form(bound, steps)
    assert simulation is not None


def test_fleet_screen_replan_edit_demand_returns_plan():
    data = _replan_form_data(
        change_type="edit_demand",
        change_demand_source="S1",
        change_demand_destination="C",
        change_demand_tons=200,
    )
    bound = FleetConfigurationForm(data)
    assert bound.is_valid(), bound.errors
    steps = []
    simulation = _run_from_form(bound, steps)
    assert simulation is not None
    assert simulation.state.route_demands
    # Demand for S1->C was updated on the live state locations
    matched = [
        v
        for (s, d), v in simulation.state.route_demands.items()
        if s.name == "S1" and d.name == "C"
    ]
    assert matched == [200]


def _formatted(simulation, steps):
    from lean_ui.fleet_ui.views import _format_steps

    return _format_steps(simulation, list(steps))
