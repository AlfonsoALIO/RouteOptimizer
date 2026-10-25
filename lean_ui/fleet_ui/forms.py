import json

from django import forms

from core.fixtures import load_toy_mine
from core.scenario import ScenarioError, load_scenario


def _json_dumps(value):
    return json.dumps(value, indent=2, sort_keys=True)


class FleetConfigurationForm(forms.Form):
    """Edit a mine scenario and dispatch horizon from the fleet screen."""

    locations_json = forms.CharField(
        label="Locations (JSON: name, resident_capacity)",
        widget=forms.Textarea(attrs={"rows": 10, "cols": 60}),
    )
    arcs_json = forms.CharField(
        label="Arcs (JSON: source, destination, travel_time_minutes)",
        widget=forms.Textarea(attrs={"rows": 12, "cols": 60}),
    )
    demands_json = forms.CharField(
        label="Demands (JSON: source, destination, tons)",
        widget=forms.Textarea(attrs={"rows": 8, "cols": 60}),
    )
    truck_capacity = forms.FloatField(
        label="Truck capacity (tons)",
        min_value=0.1,
    )
    shift_length_hours = forms.FloatField(
        label="Shift length (hours)",
        min_value=0.1,
    )
    fleet_size = forms.IntegerField(
        label="Fleet size",
        min_value=1,
    )
    num_segments = forms.IntegerField(
        label="Number of segments",
        min_value=1,
    )
    num_trucks = forms.IntegerField(
        label="Number of trucks",
        min_value=1,
    )

    @classmethod
    def initial_from_toy_mine(cls):
        scenario = load_toy_mine()
        return {
            "locations_json": _json_dumps(scenario.locations),
            "arcs_json": _json_dumps(scenario.arcs),
            "demands_json": _json_dumps(scenario.demands),
            "truck_capacity": scenario.trucks[0]["tonnage_capacity"],
            "shift_length_hours": scenario.shift_length_hours,
            "fleet_size": scenario.fleet_size,
            "num_segments": 58,
            "num_trucks": scenario.fleet_size,
        }

    @classmethod
    def from_toy_mine(cls, data=None):
        initial = cls.initial_from_toy_mine()
        if data is None:
            return cls(initial=initial)
        return cls(data, initial=initial)

    def build_scenario(self):
        """Build a validated MineScenario from cleaned form data."""
        if not hasattr(self, "cleaned_data"):
            raise RuntimeError("build_scenario requires a valid form")
        return self.cleaned_data["_scenario"]

    def clean(self):
        cleaned = super(FleetConfigurationForm, self).clean()
        if self.errors:
            return cleaned

        try:
            locations = json.loads(cleaned["locations_json"])
            arcs = json.loads(cleaned["arcs_json"])
            demands = json.loads(cleaned["demands_json"])
        except (TypeError, ValueError) as exc:
            raise forms.ValidationError("invalid JSON: %s" % exc)

        num_trucks = cleaned["num_trucks"]
        capacity = cleaned["truck_capacity"]
        trucks = [
            {"name": "truck_%i" % i, "tonnage_capacity": float(capacity)}
            for i in range(1, num_trucks + 1)
        ]

        payload = {
            "locations": locations,
            "arcs": arcs,
            "demands": demands,
            "trucks": trucks,
            "shift_length_hours": cleaned["shift_length_hours"],
            "fleet_size": cleaned["fleet_size"],
        }

        try:
            scenario = load_scenario(payload)
        except ScenarioError as exc:
            raise forms.ValidationError(str(exc))

        cleaned["_scenario"] = scenario
        return cleaned
