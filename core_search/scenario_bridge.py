"""Build search entities from a MineScenario."""

from collections import OrderedDict

from core_search.entities import Location, MineConfiguration, Truck
from core_search.state import FleetState


def fleet_state_from_scenario(scenario, num_segments, num_trucks):
    """Create a FleetState from a scenario.

    Segment count and truck count come from the caller (fleet form).
    Arc travel times become the search movement cost in minutes.
    """
    locations_by_name = {}
    for loc in scenario.locations:
        capacity = loc["resident_capacity"]
        if loc["name"] == "garage":
            capacity = num_trucks
        locations_by_name[loc["name"]] = Location(loc["name"], capacity)

    connections = [
        (locations_by_name[arc["source"]], locations_by_name[arc["destination"]])
        for arc in scenario.arcs
    ]
    travel_times = {
        (
            locations_by_name[arc["source"]],
            locations_by_name[arc["destination"]],
        ): float(arc["travel_time_minutes"])
        for arc in scenario.arcs
    }
    config = MineConfiguration(connections, travel_times=travel_times)

    capacity = 100.0
    if scenario.trucks:
        capacity = scenario.trucks[0]["tonnage_capacity"]
    trucks = [
        Truck("truck_%i" % i, capacity) for i in range(1, num_trucks + 1)
    ]

    demands = OrderedDict()
    for demand in scenario.demands:
        key = (
            locations_by_name[demand["source"]],
            locations_by_name[demand["destination"]],
        )
        demands[key] = demand["tons"]

    return FleetState(
        config,
        trucks,
        demands,
        num_segments,
        shift_length_hours=scenario.shift_length_hours,
    )
