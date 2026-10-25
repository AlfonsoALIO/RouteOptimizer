"""Build a MineScenario from haul history rows (loader -> destination arcs)."""

from collections import defaultdict

from core.scenario import ScenarioError, load_scenario


def scenario_from_haul_rows(
    rows,
    demands=None,
    trucks=None,
    resident_capacity=None,
    shift_length_hours=None,
    fleet_size=None,
):
    """Convert haul rows into a validated scenario.

    Each row must include loader (CargCo), destination, and haul_time.
    Travel time on each loader-destination arc is the mean haul_time in minutes.
    Distance is averaged when present on the rows.
    """
    required_caller = {
        "demands": demands,
        "trucks": trucks,
        "resident_capacity": resident_capacity,
        "shift_length_hours": shift_length_hours,
        "fleet_size": fleet_size,
    }
    for field, value in required_caller.items():
        if value is None:
            raise ScenarioError("missing required field: %s" % field)

    if not isinstance(rows, (list, tuple)):
        raise ScenarioError("rows must be a list")

    pairs = defaultdict(lambda: {"haul_times": [], "distances": []})

    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ScenarioError("each haul row must be a mapping")

        for field in ("loader", "destination", "haul_time"):
            if field not in row or row[field] is None or row[field] == "":
                raise ScenarioError("missing required field: %s" % field)

        loader = row["loader"]
        destination = row["destination"]
        try:
            haul_time = float(row["haul_time"])
        except (TypeError, ValueError):
            raise ScenarioError("missing required field: haul_time")

        key = (loader, destination)
        pairs[key]["haul_times"].append(haul_time)
        if row.get("distance") is not None and row.get("distance") != "":
            pairs[key]["distances"].append(float(row["distance"]))

    if not pairs:
        raise ScenarioError("rows must be a non-empty list")

    location_names = set()
    arcs = []
    for (source, destination), stats in sorted(pairs.items()):
        location_names.add(source)
        location_names.add(destination)
        mean_ht = sum(stats["haul_times"]) / float(len(stats["haul_times"]))
        arc = {
            "source": source,
            "destination": destination,
            "travel_time_minutes": float(mean_ht),
        }
        if stats["distances"]:
            arc["distance"] = sum(stats["distances"]) / float(len(stats["distances"]))
        arcs.append(arc)

    locations = [
        {"name": name, "resident_capacity": int(resident_capacity)}
        for name in sorted(location_names)
    ]

    return load_scenario(
        {
            "locations": locations,
            "arcs": arcs,
            "demands": demands,
            "trucks": trucks,
            "shift_length_hours": shift_length_hours,
            "fleet_size": fleet_size,
        }
    )
