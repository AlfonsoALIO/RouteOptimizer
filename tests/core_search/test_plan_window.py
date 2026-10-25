"""Story 4.1: plan the next k segments from the current fleet."""

from collections import OrderedDict

from core_search.entities import Location, MineConfiguration, Truck
from core_search.replan import plan_window
from core_search.state import Action, FleetState, Movement


def _replan_mine(max_segment=12, shift_hours=2.0):
    garage = Location("garage", 4)
    shovel = Location("S", 2)
    crusher = Location("C", 2)
    connections = [
        (garage, shovel),
        (shovel, garage),
        (shovel, crusher),
        (crusher, shovel),
        (crusher, garage),
    ]
    travel_times = {edge: 10.0 for edge in connections}
    config = MineConfiguration(connections, travel_times=travel_times)
    trucks = [Truck("truck_1", 100), Truck("truck_2", 100)]
    demands = OrderedDict([((shovel, crusher), 200)])
    state = FleetState(
        config,
        trucks,
        demands,
        max_segment=max_segment,
        shift_length_hours=shift_hours,
    )
    return state, garage, shovel, crusher


def test_k_zero_produces_no_new_movements():
    state, garage, shovel, crusher = _replan_mine()
    truck = state.trucks[0]
    state.resident_trucks[garage].remove(truck)
    state.resident_trucks[shovel].add(truck)

    solution = plan_window(state, k=0)

    assert solution is not None
    assert solution.state.segment == state.segment
    assert all(n.action is None or not n.action.movements for n in solution.path_from_root())


def test_already_at_shift_end_produces_no_new_movements():
    state, garage, shovel, crusher = _replan_mine(max_segment=8)
    state.segment = state.max_segment

    solution = plan_window(state, k=5)

    assert solution is not None
    assert solution.state.segment == state.max_segment
    assert all(n.action is None or not n.action.movements for n in solution.path_from_root())


def test_mid_shift_window_starts_from_positions_and_skips_garage():
    state, garage, shovel, crusher = _replan_mine(max_segment=20)
    t1, t2 = state.trucks
    # Mid-shift: one truck at the shovel, one still traveling garage -> shovel
    state.segment = 4
    state.resident_trucks[garage].clear()
    state.resident_trucks[shovel].add(t1)
    state.in_transit[t2] = (garage, shovel, 15.0)
    state.covered_demands[(shovel, crusher)] = 0

    before_covered = state.total_covered_demand()
    # First action must not reassign the in-transit truck
    first_actions = state.possible_actions()
    for action in first_actions:
        assert all(m.truck != t2 for m in action.movements)

    solution = plan_window(state, k=3)

    assert solution is not None
    assert solution.state.segment == 4 + 3
    assert solution.state.total_covered_demand() >= before_covered
    # Mid-shift: garage return is not required
    assert solution.state.segment < solution.state.max_segment
    assert not solution.state.is_successful()


def test_mid_shift_prefers_more_demand_then_less_travel():
    state, garage, shovel, crusher = _replan_mine(max_segment=20)
    t1 = state.trucks[0]
    state.segment = 2
    state.resident_trucks[garage].clear()
    state.resident_trucks[shovel].add(t1)
    # Second truck stays unused in garage so idle is possible
    state.resident_trucks[garage].add(state.trucks[1])

    solution = plan_window(state, k=2)
    assert solution is not None
    # With a truck on the shovel, hauling beats pure idle on covered demand
    assert solution.state.covered_demands[(shovel, crusher)] >= 100


def test_window_to_shift_end_requires_garage_and_full_demand():
    state, garage, shovel, crusher = _replan_mine(max_segment=16)
    # Start from the garage at the beginning; k reaches the shift end
    solution = plan_window(state, k=state.max_segment)

    assert solution is not None
    assert solution.state.segment <= solution.state.max_segment
    assert len(solution.state.resident_trucks[garage]) == len(state.trucks)
    assert not solution.state.in_transit
    assert solution.state.total_covered_demand() >= sum(state.route_demands.values())
