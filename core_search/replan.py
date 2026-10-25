"""Plan the next k segments from a current fleet state."""

import heapq
import json

from core_search.run import _heuristic
from core_search.search import AStar, Node

CLOSE_SHOVEL = "close_shovel"
FULL_QUEUE = "full_queue"
EDIT_DEMAND = "edit_demand"

CHANGE_TYPES = (CLOSE_SHOVEL, FULL_QUEUE, EDIT_DEMAND)


def _location_by_name(state, name):
    for loc in state.config.locations():
        if loc.name == name:
            return loc
    raise ValueError("unknown location: %s" % name)


def apply_mine_change(state, change_type, location=None, source=None, destination=None, tons=None):
    """Apply one mine change onto ``state`` (mutates in place)."""
    if change_type == CLOSE_SHOVEL:
        if not location:
            raise ValueError("close_shovel requires location")
        loc = _location_by_name(state, location)
        loc.resident_capacity = 0
        return state

    if change_type == FULL_QUEUE:
        if not location:
            raise ValueError("full_queue requires location")
        loc = _location_by_name(state, location)
        # Freeze the queue as full at its current occupancy
        loc.resident_capacity = len(state.resident_trucks[loc])
        return state

    if change_type == EDIT_DEMAND:
        if not source or not destination or tons is None:
            raise ValueError("edit_demand requires source, destination, and tons")
        src = _location_by_name(state, source)
        dst = _location_by_name(state, destination)
        key = (src, dst)
        tons = float(tons)
        if tons < 0:
            raise ValueError("demand tons must be non-negative")
        state.route_demands[key] = tons
        if key not in state.covered_demands:
            state.covered_demands[key] = 0
        if state.covered_demands[key] > tons:
            state.covered_demands[key] = tons
        return state

    raise ValueError("unknown change type: %s" % change_type)


def apply_fleet_snapshot(state, snapshot):
    """Load resident and in-transit truck positions from a snapshot mapping."""
    if snapshot is None:
        return state
    if isinstance(snapshot, str):
        snapshot = json.loads(snapshot)

    trucks_by_name = {t.name: t for t in state.trucks}
    for loc in state.resident_trucks:
        state.resident_trucks[loc].clear()
    state.in_transit.clear()

    if "segment" in snapshot:
        state.segment = int(snapshot["segment"])

    for loc_name, truck_names in (snapshot.get("residents") or {}).items():
        loc = _location_by_name(state, loc_name)
        for name in truck_names:
            truck = trucks_by_name[name]
            state.resident_trucks[loc].add(truck)

    for entry in snapshot.get("in_transit") or []:
        truck = trucks_by_name[entry["truck"]]
        src = _location_by_name(state, entry["source"])
        dst = _location_by_name(state, entry["destination"])
        remaining = float(entry["remaining_minutes"])
        state.in_transit[truck] = (src, dst, remaining)

    placed = set()
    for trucks in state.resident_trucks.values():
        placed.update(trucks)
    placed.update(state.in_transit.keys())
    for truck in state.trucks:
        if truck not in placed:
            state.resident_trucks[state.garage].add(truck)

    return state


def plan_window(fleet_state, k, listener=None):
    """Solve a k-segment dispatch window starting from ``fleet_state``.

    Mid-shift windows maximize covered demand, then minimize travel time, and
    do not require trucks in the garage. A window that reaches the shift end
    requires full demand coverage and every truck in the garage.

    When ``k`` is zero or the fleet is already at the shift end, returns the
    current state with no new movements.
    """
    state = fleet_state.clone()

    if k <= 0 or state.segment >= state.max_segment:
        return Node(state, cost=state.trips)

    window_end = min(state.segment + k, state.max_segment)
    state.planning_horizon_end = window_end
    reaches_shift_end = window_end >= state.max_segment

    if reaches_shift_end:
        return AStar(state, _heuristic, listener).solve()

    return _solve_open_window(state, listener)


def replan(
    fleet_state,
    k,
    change_type=None,
    location=None,
    source=None,
    destination=None,
    tons=None,
    fleet_snapshot=None,
    listener=None,
):
    """Replan k segments after an optional mine change from the current fleet."""
    state = fleet_state.clone()
    if fleet_snapshot is not None:
        apply_fleet_snapshot(state, fleet_snapshot)
    if change_type:
        apply_mine_change(
            state,
            change_type,
            location=location,
            source=source,
            destination=destination,
            tons=tons,
        )
    return plan_window(state, k, listener=listener)


def _window_rank(state):
    """Higher is better: more tons first, then less travel time."""
    return (state.total_covered_demand(), -state.trips)


def _solve_open_window(state, listener=None):
    """Enumerate reachable states through the window; keep the best leaf."""
    root = Node(state, cost=state.trips)
    explored = set()
    queue = []
    heapq.heappush(queue, (state.trips, root))
    best = None
    num = 0

    while queue:
        _, node = heapq.heappop(queue)
        if node in explored:
            continue
        explored.add(node)
        num += 1
        current = node.state

        if listener:
            listener(
                (
                    num,
                    node.cost,
                    current.trips,
                    current.segment,
                    current.total_covered_demand(),
                )
            )

        at_horizon = current.segment >= current.planning_horizon_end
        actions = [] if at_horizon else current.possible_actions()

        if at_horizon or not actions:
            if best is None or _window_rank(current) > _window_rank(best.state):
                best = node
            continue

        for action in actions:
            new_state = current.clone()
            new_state.execute_action(action)
            child = Node(new_state, cost=new_state.trips, action=action, parent=node)
            if child in explored:
                continue
            heapq.heappush(queue, (new_state.trips, child))

    return best
