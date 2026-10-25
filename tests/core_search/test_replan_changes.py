"""Story 4.2: replan when the mine changes."""

from collections import OrderedDict

from core_search.entities import Location, MineConfiguration, Truck
from core_search.replan import (
    CLOSE_SHOVEL,
    EDIT_DEMAND,
    FULL_QUEUE,
    apply_mine_change,
    replan,
)
from core_search.state import FleetState


def _change_mine(max_segment=16):
    garage = Location("garage", 4)
    shovel = Location("S", 2)
    dump = Location("D", 2)
    crusher = Location("C", 2)
    connections = [
        (garage, shovel),
        (garage, dump),
        (shovel, garage),
        (dump, garage),
        (shovel, crusher),
        (crusher, shovel),
        (dump, crusher),
        (crusher, dump),
        (crusher, garage),
    ]
    travel_times = {edge: 8.0 for edge in connections}
    config = MineConfiguration(connections, travel_times=travel_times)
    trucks = [Truck("truck_1", 100), Truck("truck_2", 100)]
    demands = OrderedDict([((shovel, crusher), 200), ((dump, crusher), 100)])
    state = FleetState(
        config,
        trucks,
        demands,
        max_segment=max_segment,
        shift_length_hours=2.0,
    )
    return state, garage, shovel, dump, crusher


def test_closed_shovel_gets_no_new_arrivals_and_transit_stays():
    state, garage, shovel, dump, crusher = _change_mine()
    t1, t2 = state.trucks
    state.segment = 3
    state.resident_trucks[garage].clear()
    state.resident_trucks[dump].add(t1)
    state.in_transit[t2] = (garage, shovel, 20.0)

    apply_mine_change(state, CLOSE_SHOVEL, location="S")
    assert shovel.resident_capacity == 0

    for action in state.possible_actions():
        for movement in action.movements:
            assert movement.destination != shovel
            assert movement.truck != t2

    solution = replan(state, k=3, change_type=CLOSE_SHOVEL, location="S")
    assert solution is not None
    for node in solution.path_from_root():
        if not node.action:
            continue
        for movement in node.action.movements:
            assert movement.destination != shovel


def test_full_queue_rejects_new_arrivals():
    state, garage, shovel, dump, crusher = _change_mine()
    t1, t2 = state.trucks
    state.segment = 2
    state.resident_trucks[garage].clear()
    state.resident_trucks[dump].add(t1)
    state.resident_trucks[garage].add(t2)

    apply_mine_change(state, FULL_QUEUE, location="D")
    assert dump.resident_capacity == 1
    assert state._open_slots(dump) == 0

    for action in state.possible_actions():
        for movement in action.movements:
            assert movement.destination != dump


def test_edited_demand_is_used_from_current_positions():
    state, garage, shovel, dump, crusher = _change_mine()
    t1 = state.trucks[0]
    state.segment = 2
    state.resident_trucks[garage].remove(t1)
    state.resident_trucks[shovel].add(t1)

    solution = replan(
        state,
        k=4,
        change_type=EDIT_DEMAND,
        source="S",
        destination="C",
        tons=100,
    )
    assert solution is not None
    assert solution.state.route_demands[(shovel, crusher)] == 100
    assert solution.state.covered_demands[(shovel, crusher)] <= 100
    assert solution.state.total_covered_demand() >= 100
