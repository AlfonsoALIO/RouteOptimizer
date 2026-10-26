"""Deterministic synthetic mine scenarios (format version 1).

These are invented graphs for demos and benchmarks. They are not haul history
and not a real mine.
"""

from __future__ import annotations

# fleet, capacity_tons, travel_minutes, shift_hours, tons_per_shovel, shovel_queue
SHUTTLE = (
    (2, 100.0, 15.0, 1.0, 100.0, 2),
    (2, 100.0, 15.0, 1.0, 200.0, 2),
    (2, 50.0, 10.0, 1.0, 50.0, 1),
    (3, 100.0, 15.0, 2.0, 200.0, 2),
    (4, 150.0, 20.0, 2.0, 300.0, 2),
    (4, 100.0, 15.0, 4.0, 400.0, 2),
    (6, 100.0, 15.0, 4.0, 600.0, 2),
    (2, 100.0, 30.0, 1.0, 500.0, 1),  # high demand, short shift
)

# two shovels feeding one crusher
TWO_SHOVEL = (
    (2, 100.0, 15.0, 2.0, 100.0, 1),
    (3, 100.0, 15.0, 2.0, 150.0, 2),
    (4, 100.0, 20.0, 4.0, 200.0, 2),
    (4, 200.0, 15.0, 4.0, 400.0, 2),
    (6, 100.0, 10.0, 4.0, 300.0, 2),
    (8, 100.0, 15.0, 8.0, 400.0, 2),
)

# one shovel, ore to crusher and waste to dump
ORE_WASTE = (
    (2, 100.0, 15.0, 2.0, 100.0, 2),
    (3, 100.0, 15.0, 2.0, 150.0, 2),
    (4, 100.0, 20.0, 4.0, 200.0, 2),
    (4, 150.0, 15.0, 4.0, 300.0, 2),
    (6, 100.0, 15.0, 8.0, 400.0, 2),
    (2, 100.0, 30.0, 1.0, 400.0, 1),
)


def _trucks(fleet, capacity):
    return [
        {"name": "truck_%i" % i, "tonnage_capacity": float(capacity)}
        for i in range(1, int(fleet) + 1)
    ]


def _arc(source, destination, minutes):
    return {
        "source": source,
        "destination": destination,
        "travel_time_minutes": float(minutes),
    }


def _link(a, b, minutes, arcs):
    arcs.append(_arc(a, b, minutes))
    arcs.append(_arc(b, a, minutes))


def _location(name, capacity):
    return {"name": name, "resident_capacity": int(capacity)}


def _finish(locations, arcs, demands, fleet, capacity, shift_hours):
    return {
        "format_version": "1",
        "locations": locations,
        "arcs": arcs,
        "demands": demands,
        "trucks": _trucks(fleet, capacity),
        "shift_length_hours": float(shift_hours),
        "fleet_size": int(fleet),
    }


def shuttle_scenario(fleet, capacity, travel, shift_hours, tons, shovel_queue):
    """Garage → shovel → crusher."""
    locations = [
        _location("garage", fleet),
        _location("S", shovel_queue),
        _location("C", max(1, shovel_queue)),
    ]
    arcs = []
    _link("garage", "S", travel, arcs)
    _link("S", "C", travel, arcs)
    _link("C", "garage", travel, arcs)
    demands = [{"source": "S", "destination": "C", "tons": float(tons)}]
    return _finish(locations, arcs, demands, fleet, capacity, shift_hours)


def two_shovel_scenario(fleet, capacity, travel, shift_hours, tons_each, shovel_queue):
    """Two shovels feeding one crusher."""
    locations = [
        _location("garage", fleet),
        _location("S1", shovel_queue),
        _location("S2", shovel_queue),
        _location("C", max(2, shovel_queue)),
    ]
    arcs = []
    for shovel in ("S1", "S2"):
        _link("garage", shovel, travel, arcs)
        _link(shovel, "C", travel, arcs)
    _link("C", "garage", travel, arcs)
    demands = [
        {"source": "S1", "destination": "C", "tons": float(tons_each)},
        {"source": "S2", "destination": "C", "tons": float(tons_each) * 0.5},
    ]
    return _finish(locations, arcs, demands, fleet, capacity, shift_hours)


def ore_waste_scenario(fleet, capacity, travel, shift_hours, ore_tons, shovel_queue):
    """One shovel: ore to crusher, waste to dump."""
    locations = [
        _location("garage", fleet),
        _location("S", shovel_queue),
        _location("C", max(1, shovel_queue)),
        _location("W", max(1, shovel_queue)),
    ]
    arcs = []
    _link("garage", "S", travel, arcs)
    _link("S", "C", travel, arcs)
    _link("S", "W", travel * 1.25, arcs)
    _link("C", "garage", travel, arcs)
    _link("W", "garage", travel * 1.25, arcs)
    demands = [
        {"source": "S", "destination": "C", "tons": float(ore_tons)},
        {"source": "S", "destination": "W", "tons": float(ore_tons) * 0.4},
    ]
    return _finish(locations, arcs, demands, fleet, capacity, shift_hours)


def synthetic_catalog():
    """Return catalog rows: id, family, seed, scenario payload (no solver labels)."""
    rows = []

    def add(family, index, payload):
        rows.append(
            {
                "id": "%s-%03d" % (family, index),
                "family": family,
                "seed": 1000 + len(rows),
                "synthetic": True,
                "source": "generated",
                "scenario": payload,
            }
        )

    for index, spec in enumerate(SHUTTLE, start=1):
        add("shuttle", index, shuttle_scenario(*spec))
    for index, spec in enumerate(TWO_SHOVEL, start=1):
        add("two_shovel", index, two_shovel_scenario(*spec))
    for index, spec in enumerate(ORE_WASTE, start=1):
        add("ore_waste", index, ore_waste_scenario(*spec))
    return rows


def catalog_features(row):
    """Flat columns used by the dataset table."""
    scenario = row["scenario"]
    capacities = [float(t["tonnage_capacity"]) for t in scenario["trucks"]]
    total_tons = sum(float(d["tons"]) for d in scenario["demands"])
    return {
        "id": row["id"],
        "family": row["family"],
        "seed": int(row["seed"]),
        "synthetic": True,
        "source": row.get("source", "generated"),
        "fleet_size": int(scenario["fleet_size"]),
        "shift_length_hours": float(scenario["shift_length_hours"]),
        "n_locations": len(scenario["locations"]),
        "n_arcs": len(scenario["arcs"]),
        "n_demands": len(scenario["demands"]),
        "total_tons": total_tons,
        "truck_capacity_tons": capacities[0] if capacities else 0.0,
    }
