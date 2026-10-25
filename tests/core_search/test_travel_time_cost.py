"""Story 3.2: dispatch cost is arc travel time in minutes."""

from collections import OrderedDict

from core_search.entities import Location, MineConfiguration, Truck
from core_search.run import _heuristic, run
from core_search.search import AStar
from core_search.state import Action, FleetState, Movement


def _minute_mine(haul_minutes, return_minutes=4.0, to_shovel_minutes=3.0):
    """One-truck mine: garage -> S -> C (demand) , returns via C -> garage."""
    garage = Location("garage", 1)
    shovel = Location("S", 1)
    crusher = Location("C", 1)
    connections = [
        (garage, shovel),
        (shovel, crusher),
        (crusher, shovel),
        (shovel, garage),
        (crusher, garage),
    ]
    travel_times = {
        (garage, shovel): to_shovel_minutes,
        (shovel, crusher): haul_minutes,
        (crusher, shovel): 1.0,
        (shovel, garage): return_minutes,
        (crusher, garage): return_minutes,
    }
    config = MineConfiguration(connections, travel_times=travel_times)
    trucks = [Truck("truck_1", 100)]
    demands = OrderedDict([((shovel, crusher), 100)])
    return FleetState(config, trucks, demands, max_segment=20), garage, shovel, crusher


def test_movement_cost_is_arc_travel_time_minutes():
    state, garage, shovel, crusher = _minute_mine(haul_minutes=17.0, to_shovel_minutes=12.0)
    truck = state.trucks[0]

    state.execute_action(Action(Movement(truck, garage, shovel)))

    assert state.trips == 12.0


def test_demand_haul_costs_arc_travel_time():
    state, garage, shovel, crusher = _minute_mine(haul_minutes=17.0)
    truck = state.trucks[0]
    # Place truck at shovel
    state.resident_trucks[garage].clear()
    state.resident_trucks[shovel].add(truck)

    state.execute_action(Action(Movement(truck, shovel, crusher)))

    assert state.trips == 17.0
    # Demand shortcut: haul is costed and credited; truck stays at the shovel
    assert truck in state.resident_trucks[shovel]
    assert state.covered_demands[(shovel, crusher)] == 100


def test_heuristic_is_minutes_not_trip_count():
    state, garage, shovel, crusher = _minute_mine(haul_minutes=15.0)
    # 100 tons left, one 100-ton truck, dest capacity 1 -> one dispatch * 15 min
    assert _heuristic(state) == 15.0
    # Former trip-count heuristic was segments + trucks_taken (== 2), not minutes
    assert _heuristic(state) != 2


def test_search_returns_lower_travel_time_dispatch():
    short_state, _, _, _ = _minute_mine(haul_minutes=10.0)
    long_state, _, _, _ = _minute_mine(haul_minutes=40.0)

    short = AStar(short_state, _heuristic).solve()
    long = AStar(long_state, _heuristic).solve()

    assert short is not None and long is not None
    # Same demand covered; shorter haul arc must win on total minutes
    assert short.cost < long.cost
    # Minimum: garage->S (3) + haul + C->garage (4)
    assert short.cost == 3.0 + 10.0 + 4.0
    assert long.cost == 3.0 + 40.0 + 4.0


def test_toy_mine_objective_is_minutes_and_completes():
    solution = run(num_segments=58, num_trucks=21)
    assert solution is not None
    assert solution.cost > 0
    # Toy arcs are 15 minutes; objective is travel time, not trip count (~190)
    assert solution.cost == solution.state.trips
    assert solution.cost % 15 == 0
    assert solution.cost >= 15 * 190
