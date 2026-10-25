"""Story 2.2: dispatcher runs on the named toy-mine fixture."""

from core.fixtures import TOY_MINE_NAME, load_toy_mine
from core_search.run import run


def test_toy_mine_fixture_is_valid_scenario():
    scenario = load_toy_mine()

    names = {loc["name"] for loc in scenario.locations}
    assert names == {"S1", "S2", "L1", "L2", "W", "C", "garage"}
    assert TOY_MINE_NAME == "toy_mine"

    working = [loc for loc in scenario.locations if loc["name"] != "garage"]
    assert len(working) == 6
    assert all(loc["resident_capacity"] == 2 for loc in working)

    assert all(arc["travel_time_minutes"] > 0 for arc in scenario.arcs)
    assert len(scenario.arcs) == 20

    demand_map = {
        (d["source"], d["destination"]): d["tons"] for d in scenario.demands
    }
    assert demand_map == {
        ("S1", "C"): 8000,
        ("S2", "C"): 1200,
        ("L1", "C"): 4000,
        ("S1", "W"): 1600,
        ("S2", "W"): 2000,
        ("L1", "W"): 1000,
    }

    assert all(t["tonnage_capacity"] == 100 for t in scenario.trucks)


def test_dispatch_runs_on_fixture_without_sql():
    solution = run(num_segments=58, num_trucks=21)

    assert solution is not None
    assert solution.cost > 0

    # Search still uses trip-count objective; arcs carry travel time unused for cost
    scenario = load_toy_mine()
    assert all("travel_time_minutes" in arc for arc in scenario.arcs)


def test_dispatch_uses_requested_truck_count_and_horizon():
    solution = run(num_segments=58, num_trucks=21)
    assert solution is not None

    root = solution.path_from_root()[0]
    assert root.state.max_segment == 58
    assert len(root.state.trucks) == 21
