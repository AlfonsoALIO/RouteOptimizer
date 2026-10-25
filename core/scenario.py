"""Shared mine scenario for the dispatcher and the batch solvers.

Units:
  - demand and truck capacity: tons
  - shift length: hours
  - arc travel time: minutes
"""

REQUIRED_FIELDS = (
    "locations",
    "arcs",
    "demands",
    "trucks",
    "shift_length_hours",
    "fleet_size",
)


class ScenarioError(ValueError):
    """Raised when a scenario payload is incomplete or inconsistent."""


class MineScenario(object):
    """One mine description both solvers can consume."""

    UNITS = {
        "demand": "tons",
        "truck_capacity": "tons",
        "shift_length": "hours",
        "travel_time": "minutes",
    }

    def __init__(
        self,
        locations,
        arcs,
        demands,
        trucks,
        shift_length_hours,
        fleet_size,
    ):
        self.locations = locations
        self.arcs = arcs
        self.demands = demands
        self.trucks = trucks
        self.shift_length_hours = shift_length_hours
        self.fleet_size = fleet_size


def _require_mapping(payload):
    if not isinstance(payload, dict):
        raise ScenarioError("scenario payload must be a mapping")


def _require_fields(payload):
    for field in REQUIRED_FIELDS:
        if field not in payload:
            raise ScenarioError("missing required field: %s" % field)


def _location_names(locations):
    if not isinstance(locations, (list, tuple)) or len(locations) == 0:
        raise ScenarioError("locations must be a non-empty list")

    names = []
    seen = set()
    for loc in locations:
        if not isinstance(loc, dict) or "name" not in loc or "resident_capacity" not in loc:
            raise ScenarioError(
                "each location must include name and resident_capacity"
            )
        name = loc["name"]
        if name in seen:
            raise ScenarioError("duplicate location: %s" % name)
        seen.add(name)
        names.append(name)
    return set(names)


def _normalize_arcs(arcs, known_locations):
    if not isinstance(arcs, (list, tuple)):
        raise ScenarioError("arcs must be a list")

    normalized = []
    for arc in arcs:
        if not isinstance(arc, dict):
            raise ScenarioError("each arc must be a mapping")
        for field in ("source", "destination", "travel_time_minutes"):
            if field not in arc:
                raise ScenarioError("missing required field: %s" % field)

        source = arc["source"]
        destination = arc["destination"]
        if source not in known_locations:
            raise ScenarioError("unknown location: %s" % source)
        if destination not in known_locations:
            raise ScenarioError("unknown location: %s" % destination)

        travel = arc["travel_time_minutes"]
        if travel is None or float(travel) <= 0:
            raise ScenarioError("travel_time_minutes must be positive")

        item = {
            "source": source,
            "destination": destination,
            "travel_time_minutes": float(travel),
        }
        if arc.get("distance") is not None and arc.get("distance") != "":
            item["distance"] = float(arc["distance"])
        normalized.append(item)
    return normalized


def _normalize_demands(demands, known_locations):
    if not isinstance(demands, (list, tuple)):
        raise ScenarioError("demands must be a list")

    normalized = []
    for demand in demands:
        if not isinstance(demand, dict):
            raise ScenarioError("each demand must be a mapping")
        for field in ("source", "destination", "tons"):
            if field not in demand:
                raise ScenarioError("missing required field: %s" % field)

        source = demand["source"]
        destination = demand["destination"]
        if source not in known_locations:
            raise ScenarioError("unknown location: %s" % source)
        if destination not in known_locations:
            raise ScenarioError("unknown location: %s" % destination)

        tons = demand["tons"]
        if tons is None or float(tons) < 0:
            raise ScenarioError("tons must be non-negative")

        normalized.append(
            {
                "source": source,
                "destination": destination,
                "tons": float(tons),
            }
        )
    return normalized


def _normalize_trucks(trucks):
    if not isinstance(trucks, (list, tuple)) or len(trucks) == 0:
        raise ScenarioError("trucks must be a non-empty list")

    normalized = []
    for truck in trucks:
        if not isinstance(truck, dict) or "name" not in truck or "tonnage_capacity" not in truck:
            raise ScenarioError(
                "each truck must include name and tonnage_capacity"
            )
        capacity = truck["tonnage_capacity"]
        if capacity is None or float(capacity) <= 0:
            raise ScenarioError("tonnage_capacity must be positive")
        normalized.append(
            {
                "name": truck["name"],
                "tonnage_capacity": float(capacity),
            }
        )
    return normalized


def _normalize_locations(locations):
    normalized = []
    for loc in locations:
        capacity = loc["resident_capacity"]
        if capacity is None or int(capacity) < 0:
            raise ScenarioError("resident_capacity must be non-negative")
        normalized.append(
            {
                "name": loc["name"],
                "resident_capacity": int(capacity),
            }
        )
    return normalized


def load_scenario(payload):
    """Load and validate a scenario mapping.

    Raises ScenarioError naming a missing field or unknown location.
    """
    _require_mapping(payload)
    _require_fields(payload)

    known = _location_names(payload["locations"])
    locations = _normalize_locations(payload["locations"])
    arcs = _normalize_arcs(payload["arcs"], known)
    demands = _normalize_demands(payload["demands"], known)
    trucks = _normalize_trucks(payload["trucks"])

    shift_length_hours = payload["shift_length_hours"]
    if shift_length_hours is None or float(shift_length_hours) <= 0:
        raise ScenarioError("shift_length_hours must be positive")

    fleet_size = payload["fleet_size"]
    if fleet_size is None or int(fleet_size) <= 0:
        raise ScenarioError("fleet_size must be positive")

    return MineScenario(
        locations=locations,
        arcs=arcs,
        demands=demands,
        trucks=trucks,
        shift_length_hours=float(shift_length_hours),
        fleet_size=int(fleet_size),
    )
