from django.shortcuts import render

import core_search.run
from core.fixtures import load_toy_mine
from core_search.replan import replan
from core_search.scenario_bridge import fleet_state_from_scenario

from .forms import FleetConfigurationForm


def _format_steps(simulation, steps):
    if not simulation:
        return steps

    steps.append("")
    steps.append("Total travel time: %s minutes" % simulation.cost)
    steps.append("")
    nodes = simulation.path_from_root()
    prev_seg = 1
    for ix, n in enumerate(nodes):
        if n.action:
            s = n.state
            num_segments = s.segment - prev_seg
            prev_seg = s.segment
            steps.append(
                "Dispatch: %i\tSegments: %i\tTons moved: %i"
                % (ix, num_segments, s.total_covered_demand())
            )
            steps.append("")
            for m in n.action.movements:
                steps.append(str(m))
            steps.append("")
    return steps


def _run_from_form(form, steps):
    """Run full-shift simulate or a k-segment replan from cleaned form data."""
    scenario = form.build_scenario()
    cleaned = form.cleaned_data
    num_segments = cleaned["num_segments"]
    num_trucks = cleaned["num_trucks"]
    listener = lambda s: steps.append(
        "Iteration: %i\tEstimated Cost: %s min\tActual Cost: %s min\tSegment: %i\tProgress: %i tons"
        % s
    )

    if cleaned.get("plan_mode") == "replan":
        state = fleet_state_from_scenario(scenario, num_segments, num_trucks)
        return replan(
            state,
            cleaned["replan_k"],
            change_type=cleaned.get("change_type") or None,
            location=cleaned.get("change_location") or None,
            source=cleaned.get("change_demand_source") or None,
            destination=cleaned.get("change_demand_destination") or None,
            tons=cleaned.get("change_demand_tons"),
            fleet_snapshot=cleaned.get("_fleet_snapshot"),
            listener=listener,
        )

    return core_search.run.run(
        num_segments,
        num_trucks,
        listener=listener,
        scenario=scenario,
    )


def index(request):
    simulation = None
    steps = None
    ran = False
    scenario_error = None

    if request.method == "POST":
        form = FleetConfigurationForm.from_toy_mine(request.POST)
        if form.is_valid():
            steps = []
            simulation = _run_from_form(form, steps)
            ran = True
            steps = _format_steps(simulation, steps)
            display_scenario = form.build_scenario()
        else:
            display_scenario = load_toy_mine()
            if form.non_field_errors():
                scenario_error = "; ".join(str(e) for e in form.non_field_errors())
    else:
        form = FleetConfigurationForm.from_toy_mine()
        display_scenario = load_toy_mine()

    return render(
        request,
        "fleet_ui/index.html",
        {
            "form": form,
            "ran": ran,
            "simulation": simulation,
            "steps": steps,
            "scenario": display_scenario,
            "scenario_error": scenario_error,
        },
    )
