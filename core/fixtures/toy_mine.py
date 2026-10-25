"""Named toy-mine scenario fixture used by the fleet UI dispatcher."""

from core.scenario import load_scenario

TOY_MINE_NAME = "toy_mine"

# Uniform travel time; search costs movements by these minutes.
_DEFAULT_TRAVEL_TIME_MINUTES = 15.0

_WORKING_LOCATIONS = (
    ("S1", 2),
    ("S2", 2),
    ("L1", 2),
    ("L2", 2),
    ("W", 2),
    ("C", 2),
)

# Directed connections matching the former inline mine in core_search/run.py
_CONNECTIONS = (
    ("garage", "L1"),
    ("garage", "L2"),
    ("L1", "garage"),
    ("L2", "garage"),
    ("W", "garage"),
    ("garage", "S1"),
    ("garage", "S2"),
    ("S1", "garage"),
    ("S2", "garage"),
    ("C", "garage"),
    ("W", "L1"),
    ("L1", "W"),
    ("W", "S1"),
    ("S1", "W"),
    ("W", "S2"),
    ("S2", "W"),
    ("C", "S1"),
    ("S1", "C"),
    ("C", "S2"),
    ("S2", "C"),
    ("C", "L2"),
    ("L2", "C"),
    ("L1", "C"),
)

_DEMANDS = (
    ("S1", "C", 8000),
    ("S2", "C", 1200),
    ("L1", "C", 4000),
    ("S1", "W", 1600),
    ("S2", "W", 2000),
    ("L1", "W", 1000),
)


def toy_mine_payload():
    """Return the raw scenario mapping for the toy mine."""
    locations = [
        {"name": name, "resident_capacity": capacity}
        for name, capacity in _WORKING_LOCATIONS
    ]
    locations.append({"name": "garage", "resident_capacity": 21})

    arcs = [
        {
            "source": source,
            "destination": destination,
            "travel_time_minutes": _DEFAULT_TRAVEL_TIME_MINUTES,
        }
        for source, destination in _CONNECTIONS
    ]

    demands = [
        {"source": source, "destination": destination, "tons": float(tons)}
        for source, destination, tons in _DEMANDS
    ]

    trucks = [
        {"name": "truck_%i" % i, "tonnage_capacity": 100.0}
        for i in range(1, 22)
    ]

    return {
        "locations": locations,
        "arcs": arcs,
        "demands": demands,
        "trucks": trucks,
        "shift_length_hours": 12.0,
        "fleet_size": 21,
    }


def load_toy_mine():
    """Load the validated toy-mine scenario."""
    return load_scenario(toy_mine_payload())
