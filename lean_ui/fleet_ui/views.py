from django.shortcuts import render

import core_search.run
from core.fixtures import load_toy_mine

from .forms import FleetConfigurationForm


def _format_steps(simulation, steps):
    if not simulation:
        return steps

    steps.append("")
    steps.append("Total number of trips: %i" % simulation.cost)
    steps.append("")
    nodes = simulation.path_from_root()
    prev_seg = 1
    for ix, n in enumerate(nodes):
        if n.action:
            s = n.state
            num_segments = s.segment - prev_seg
            prev_seg = s.segment
            steps.append(
                "Dispatch: %i\tNumber of trips: %i\tTons moved: %i"
                % (ix, num_segments, s.total_covered_demand())
            )
            steps.append("")
            for m in n.action.movements:
                steps.append(str(m))
            steps.append("")
    return steps


def index(request):
    simulation = None
    steps = None
    ran = False
    scenario_error = None

    if request.method == "POST":
        form = FleetConfigurationForm.from_toy_mine(request.POST)
        if form.is_valid():
            scenario = form.build_scenario()
            num_segments = form.cleaned_data["num_segments"]
            num_trucks = form.cleaned_data["num_trucks"]
            steps = []
            simulation = core_search.run.run(
                num_segments,
                num_trucks,
                listener=lambda s: steps.append(
                    "Iteration: %i\tEstimated Cost: %i\tAcutal Cost: %i\tSegment: %i\tProgress: %i tons"
                    % s
                ),
                scenario=scenario,
            )
            ran = True
            steps = _format_steps(simulation, steps)
            display_scenario = scenario
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
