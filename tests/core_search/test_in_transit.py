"""Story 3.3: trucks stay on an arc until travel time is consumed."""

from collections import OrderedDict

from core_search.entities import Location, MineConfiguration, Truck
from core_search.search import Node
from core_search.state import Action, FleetState, Movement


def _transit_mine(travel_minutes=30.0, shift_hours=1.0, max_segment=6):
    """Garage -> shovel arc; segment length is shorter than travel when travel=30."""
    garage = Location("garage", 2)
    shovel = Location("S", 2)
    config = MineConfiguration(
        [(garage, shovel), (shovel, garage)],
        travel_times={(garage, shovel): travel_minutes, (shovel, garage): travel_minutes},
    )
    trucks = [Truck("truck_1", 100)]
    demands = OrderedDict()
    state = FleetState(
        config,
        trucks,
        demands,
        max_segment=max_segment,
        shift_length_hours=shift_hours,
    )
    return state, garage, shovel


def test_segment_advances_clock_by_shift_over_segment_count():
    state, garage, shovel = _transit_mine(shift_hours=2.0, max_segment=8)
    assert state.segment_length_minutes == 2.0 * 60.0 / 8

    before = state.clock_minutes
    state.execute_action(Action())

    assert state.segment == 2
    assert state.clock_minutes == before + state.segment_length_minutes


def test_long_haul_leaves_truck_in_transit_and_unassignable():
    # shift 1h / 6 segments = 10 min per segment; travel 30 > 10
    state, garage, shovel = _transit_mine(travel_minutes=30.0, shift_hours=1.0, max_segment=6)
    truck = state.trucks[0]

    state.execute_action(Action(Movement(truck, garage, shovel)))

    assert truck in state.in_transit
    src, dst, remaining = state.in_transit[truck]
    assert (src, dst) == (garage, shovel)
    assert remaining == 30.0 - state.segment_length_minutes
    assert truck not in state.resident_trucks[garage]
    assert truck not in state.resident_trucks[shovel]

    # Next assignment must not include the in-transit truck
    for action in state.possible_actions():
        for movement in action.movements:
            assert movement.truck != truck


def test_truck_arrives_when_remaining_fits_in_segment():
    state, garage, shovel = _transit_mine(travel_minutes=30.0, shift_hours=1.0, max_segment=6)
    truck = state.trucks[0]

    state.execute_action(Action(Movement(truck, garage, shovel)))
    assert truck in state.in_transit

    # Two more idle segments: 10 + 10 finish the remaining 20
    state.execute_action(Action())
    assert truck in state.in_transit
    state.execute_action(Action())

    assert truck not in state.in_transit
    assert truck in state.resident_trucks[shovel]


def test_in_transit_difference_makes_states_unequal():
    state_a, garage, shovel = _transit_mine(travel_minutes=30.0, shift_hours=1.0, max_segment=6)
    state_b = state_a.clone()
    truck = state_a.trucks[0]

    state_a.execute_action(Action(Movement(truck, garage, shovel)))
    # Same coverage/residents/segment pattern for B via a different remaining
    state_b.segment = state_a.segment
    state_b.clock_minutes = state_a.clock_minutes
    state_b.resident_trucks[garage].discard(truck)
    state_b.in_transit[truck] = (garage, shovel, state_a.in_transit[truck][2] + 5.0)

    assert state_a.covered_demands == state_b.covered_demands
    assert state_a.segment == state_b.segment
    assert state_a.resident_trucks[garage] == state_b.resident_trucks[garage]
    assert state_a.resident_trucks[shovel] == state_b.resident_trucks[shovel]
    assert state_a != state_b
    assert hash(state_a) != hash(state_b)

    assert Node(state_a) != Node(state_b)
