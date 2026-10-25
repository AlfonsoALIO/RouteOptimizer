"""Story 3.1: search offers alternate capacity-class assignments."""

from collections import OrderedDict

from core_search.entities import Location, MineConfiguration, Truck
from core_search.run import run
from core_search.state import Action, FleetState


def _two_arc_state():
    garage = Location("garage", 4)
    shovel = Location("S1", 2)
    crusher = Location("C", 1)
    dump = Location("W", 1)
    config = MineConfiguration(
        [
            (garage, shovel),
            (shovel, garage),
            (shovel, crusher),
            (crusher, shovel),
            (shovel, dump),
            (dump, shovel),
        ]
    )
    trucks = [Truck("truck_1", 100), Truck("truck_2", 100)]
    demands = OrderedDict(
        [
            ((shovel, crusher), 200),
            ((shovel, dump), 200),
        ]
    )
    state = FleetState(config, trucks, demands, max_segment=20)
    # Place both trucks at the shovel so demand arcs are immediately feasible
    state.resident_trucks[garage].clear()
    state.resident_trucks[shovel].update(trucks)
    return state, shovel, crusher, dump


def test_two_feasible_arcs_yield_assignments_to_either():
    state, shovel, crusher, dump = _two_arc_state()
    actions = state.possible_actions()

    assert Action() in actions

    dests_reached = set()
    for action in actions:
        for movement in action.movements:
            if movement.source == shovel:
                dests_reached.add(movement.destination)

    assert crusher in dests_reached
    assert dump in dests_reached
    # More than idle alone
    assert len(actions) > 1


def test_equal_capacity_trucks_are_not_individually_permuted():
    state, shovel, crusher, dump = _two_arc_state()
    actions = state.possible_actions()

    # Actions that only haul shovel->crusher should collapse to one by Action equality
    crusher_only = []
    for action in actions:
        if not action.movements:
            continue
        dests = {m.destination for m in action.movements}
        if dests == {crusher}:
            crusher_only.append(action)

    assert len(crusher_only) >= 1
    # All shovel->crusher-only actions compare equal (capacity-class identity)
    assert len(set(crusher_only)) == 1


def test_return_to_garage_remains_a_choice():
    state, shovel, crusher, dump = _two_arc_state()
    actions = state.possible_actions()
    garage = state.garage

    garage_returns = [
        a
        for a in actions
        if a.movements and all(m.destination == garage for m in a.movements)
    ]
    assert len(garage_returns) >= 1


def test_toy_mine_dispatch_still_completes():
    solution = run(num_segments=58, num_trucks=21)
    assert solution is not None
    assert solution.cost > 0
