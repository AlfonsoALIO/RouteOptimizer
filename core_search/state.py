"""State representation of the mine"""

import copy
import itertools as it
import math
from collections import defaultdict


class FleetState(object):
    """ Represents the current status of the fleet """

    def __init__(
        self,
        config,
        trucks,
        route_demands,
        max_segment,
        shift_length_hours=12.0,
        warm_start=False,
    ):
        """ Parameters:
                - config: MineConfiguration instance
                - truck_capacities: Map from truck name to tonnage capacity.
                    Fleet members are inferred from this parameter
                - route_demands: Map key: Tuple of locations,
                - shift_length_hours: scenario shift length; divides into segment minutes
        """

        self.config = config
        self.trucks = trucks
        self.route_demands = route_demands

        self.max_segment = max_segment
        self.shift_length_hours = float(shift_length_hours)

        if not warm_start:
            # Accumulated travel time of executed movements, in minutes
            self.trips = 0
            self.covered_demands = {k: 0 for k in route_demands}
            self.resident_trucks = {loc: set() for loc in config.locations()}
            # truck -> (source, destination, remaining_minutes)
            self.in_transit = {}
            self.segment = 1
            self.clock_minutes = 0.0
            self.segment_length_minutes = (
                self.shift_length_hours * 60.0 / float(max_segment)
            )

            self.garage = list(filter(lambda l: l.name == "garage", config.locations()))[0]

            # Assume all trucks are on the garage
            for t in self.trucks:
                self.resident_trucks[self.garage].add(t)

            # Used for the heuristic computation
            self.max_capacity = max(t.tonnage_capacity for t in trucks)
            self.num_effective_routes = sum(d.resident_capacity for s, d in route_demands)

    def __eq__(self, other):
        """Compares coverage, residents, segment, and in-transit arcs."""
        if not isinstance(other, FleetState):
            return False
        return (
            self.segment == other.segment
            and frozenset(self.covered_demands.items()) == frozenset(other.covered_demands.items())
            and self.__factorize_assignments() == other.__factorize_assignments()
            and self.__factorize_transit() == other.__factorize_transit()
        )

    def __hash__(self):
        """ Custom hash implementation to consider only elements of interest """

        elements = (
            self.segment,
            frozenset(self.covered_demands.items()),
            self.__factorize_assignments(),
            self.__factorize_transit(),
        )

        return hash(elements)

    def __factorize_assignments(self):
        """ This is a helper method to compute the hash of the state """

        # Generate tuples for the resident truck configurations of the following format:
        # (location, # of trucks, total capacity)
        return frozenset((k, len(v), sum(t.tonnage_capacity for t in v)) for k, v in self.resident_trucks.items())

    def __factorize_transit(self):
        """Bag in-transit trucks by arc, remaining minutes, and capacity class."""
        counts = defaultdict(int)
        for truck, (src, dst, remaining) in self.in_transit.items():
            counts[(src, dst, remaining, truck.tonnage_capacity)] += 1
        return frozenset(counts.items())

    def __permutate_assignemnts(self, src, trucks, locations):
        """ Returns a sequence of movements that contain all the possible assignments emanating from the source"""

        # Following the intuition behind the best answer in:
        #  https://stackoverflow.com/questions/22939260/every-way-to-organize-n-objects-in-m-list-slots
        # The "slots" are the places available on each destination. i.e. The shovel has no residing trucks
        # and a capacity of two trucks, the we can send two different trucks, hence there are two shovel slots.
        # We need the number of slots and their indices.
        slots = list(map(lambda x: x[0], sorted(
            it.chain.from_iterable(it.repeat((l, l.resident_capacity - len(self.resident_trucks[l])),
                                             l.resident_capacity - len(self.resident_trucks[l])) for l in locations
                                   ), key=lambda x: x[1], reverse=True)))

        trucks = sorted(list(trucks), key=lambda t: t.name)

        truck_capacities = {k: list(g) for k, g in it.groupby(sorted(trucks, key=lambda t: t.tonnage_capacity),
                                                              key=lambda t: t.tonnage_capacity)}

        capacity_amounts = {k: len(v) for k, v in truck_capacities.items()}
        capacity_amounts[None] = len(slots)

        # Build the movement sequence
        movements = set()
        movements_ordered = list()

        assignments = self.__helper(len(slots), capacity_amounts)

        for a in assignments:
            tc = {k: copy.copy(v) for k, v in truck_capacities.items()}
            local_movements = list()
            for ix, kind in enumerate(a):
                if kind:
                    dst = slots[ix]
                    truck = tc[kind].pop()
                    local_movements.append(Movement(truck, src, dst))
            tupled_local_movements = tuple(local_movements)
            if tupled_local_movements not in movements:
                movements.add(tupled_local_movements)
                movements_ordered.append(tupled_local_movements)

        return sorted(movements_ordered, key=lambda m: len(m), reverse=True)

    def __helper(self, slots, capacities):
        """ Helper function to the __permutate_assignments method """
        if slots == 0 or sum(capacities.values()) == 0:
            return list()
        else:
            ret = list()
            for k, v in capacities.items():
                if v > 0:
                    elem = k
                    new_capacities = copy.copy(capacities)
                    new_capacities[k] -= 1
                    reminder = self.__helper(slots - 1, new_capacities)
                    if len(reminder) > 0:
                        x = [[elem] + r for r in reminder]
                        ret.extend(x)
                    else:
                        ret.append([elem])
            return ret

    def progress(self):
        """ Returns how much of the demand is covered, normalized from zero ot one"""
        return self.total_covered_demand() / sum(self.route_demands.values())

    def total_covered_demand(self):
        """ Returns how much of the demand is covered"""
        return sum(self.covered_demands.values())

    def clone(self):
        """ Creates a new instance of the state with the same values """
        cl = FleetState(
            self.config,
            self.trucks,
            self.route_demands,
            self.max_segment,
            shift_length_hours=self.shift_length_hours,
            warm_start=True,
        )
        cl.covered_demands = {k: v for k, v in self.covered_demands.items()}
        cl.resident_trucks = {k: copy.copy(v) for k, v in self.resident_trucks.items()}
        cl.in_transit = {
            truck: (src, dst, remaining)
            for truck, (src, dst, remaining) in self.in_transit.items()
        }
        cl.trucks = self.trucks  # No need to copy this as it's immutable
        cl.trips = self.trips
        cl.segment = self.segment
        cl.clock_minutes = self.clock_minutes
        cl.segment_length_minutes = self.segment_length_minutes
        cl.garage = self.garage
        cl.max_capacity = self.max_capacity
        cl.num_effective_routes = self.num_effective_routes

        return cl

    def is_successful(self):
        """
        Returns true whether this is a successful state.
        The criteria is: All routes should have it's demand covered and all trucks should be back at the garage
        by the end of the simulation
        """

        if self.in_transit:
            return False

        # All trucks should be in the garage
        all_in_garage = len(self.resident_trucks[self.garage]) == len(self.trucks)

        if not all_in_garage:
            return False
        else:
            # All the demands must be covered
            all_covered = True
            for route in self.route_demands:
                if self.covered_demands[route] < self.route_demands[route]:
                    all_covered = False
                    break

            if self.segment <= self.max_segment and all_covered:
                return True
            else:
                return False

    def _open_slots(self, location):
        """How many more trucks can reside at location."""
        return max(0, location.resident_capacity - len(self.resident_trucks[location]))

    def _assign_by_capacity_class(self, trucks, src, dst, max_trucks, remaining_demand=None):
        """Assign trucks to one destination by capacity class (not by truck identity).

        Within a capacity class, trucks are taken in a stable name order so two
        equal-capacity trucks do not produce distinct permutations.
        """
        ordered = sorted(trucks, key=lambda t: (-t.tonnage_capacity, t.name))
        movements = []
        remaining_tons = remaining_demand
        slots_left = max_trucks

        for truck in ordered:
            if slots_left <= 0:
                break
            if remaining_tons is not None and remaining_tons <= 0:
                break
            movements.append(Movement(truck, src, dst))
            slots_left -= 1
            if remaining_tons is not None:
                remaining_tons -= truck.tonnage_capacity

        return movements

    def _greedy_movements_from(self, src):
        """Legacy per-source greedy movements (pre-Epic-3 dispatcher)."""
        config = self.config
        ds = sorted(config.destinations(src), key=lambda l: l.name)
        local_trucks = sorted(
            self.resident_trucks[src],
            key=lambda tr: tr.tonnage_capacity,
            reverse=True,
        )
        movements = []

        destinations_with_demand = []
        destinations_without_demand = []
        for d in ds:
            if (src, d) in self.route_demands:
                destinations_with_demand.append(d)
            else:
                destinations_without_demand.append(d)

        for d in destinations_with_demand:
            key = (src, d)
            if self.covered_demands[key] < self.route_demands[key]:
                remaining_demand = self.route_demands[key] - self.covered_demands[key]
                for _ in range(d.resident_capacity):
                    if remaining_demand > 0 and len(local_trucks) > 0:
                        t = local_trucks.pop()
                        movements.append(Movement(t, src, d))
                        remaining_demand -= t.tonnage_capacity
                    else:
                        break

        eligible_ds = []
        for d in destinations_without_demand:
            for d2 in config.destinations(d):
                key = (d, d2)
                if key in self.route_demands:
                    remaining_demand = self.route_demands[key] - self.covered_demands[key]
                    if remaining_demand > 0:
                        eligible_ds.append(d)
                        break

        for d in eligible_ds:
            if len(local_trucks) > 0:
                num_slots = d.resident_capacity - len(self.resident_trucks[d])
                for _ in range(num_slots):
                    if not local_trucks:
                        break
                    t = local_trucks.pop()
                    movements.append(Movement(t, src, d))
            else:
                break

        if src != self.garage:
            for t in local_trucks:
                movements.append(Movement(t, src, self.garage))

        return movements

    def _open_demand_destinations(self, src):
        """Destinations from src that still have uncovered haul demand."""
        open_ds = []
        for d in sorted(self.config.destinations(src), key=lambda l: l.name):
            key = (src, d)
            if key in self.route_demands and self.covered_demands[key] < self.route_demands[key]:
                open_ds.append(d)
        return open_ds

    def possible_actions(self):
        """Return the greedy assignment plus alternate capacity-class choices.

        The greedy combined move matches the pre-Epic-3 dispatcher. When a
        source faces two or more open demand arcs, also offer sending that
        source's trucks onto each arc alone (other sources keep their greedy
        moves), plus idle and return-to-garage.
        """

        if self.segment >= self.max_segment:
            return list()

        occupied = sorted(
            [l for l in self.resident_trucks if len(self.resident_trucks[l]) > 0],
            key=lambda l: l.name,
        )
        greedy_by_src = {src: self._greedy_movements_from(src) for src in occupied}

        actions = []
        seen = set()

        def add_action(action):
            if action not in seen:
                seen.add(action)
                actions.append(action)

        add_action(Action())

        all_greedy = [m for src in occupied for m in greedy_by_src[src]]
        if all_greedy:
            add_action(Action(*all_greedy))

        # Capacity-class branching is only expanded when a single source is
        # occupied. Multi-source fleets (e.g. the 21-truck toy mine) keep the
        # legacy greedy+idle fringe so A* stays tractable; unit scenarios with
        # trucks already at one shovel still see both arcs, idle, and garage.
        if len(occupied) != 1:
            return actions

        src = occupied[0]
        demand_open = self._open_demand_destinations(src)
        if len(demand_open) < 2:
            return actions

        local_trucks = list(self.resident_trucks[src])
        for d in demand_open:
            remaining = self.route_demands[(src, d)] - self.covered_demands[(src, d)]
            # Unassigned local trucks stay put (idle); garage return is its own action.
            branch = self._assign_by_capacity_class(
                local_trucks,
                src,
                d,
                d.resident_capacity,
                remaining_demand=remaining,
            )
            if branch:
                add_action(Action(*branch))

        if src != self.garage and local_trucks:
            garage_moves = self._assign_by_capacity_class(
                local_trucks, src, self.garage, len(local_trucks)
            )
            if garage_moves:
                add_action(Action(*garage_moves))

        return actions

    def _arrive(self, truck, source, destination):
        """Place a truck at destination and credit demand if this was a haul arc."""
        self.resident_trucks[destination].add(truck)
        key = (source, destination)
        if key in self.route_demands:
            remaining = self.route_demands[key] - self.covered_demands[key]
            if remaining > 0:
                self.covered_demands[key] += min(truck.tonnage_capacity, remaining)

    def _progress_transit(self, minutes):
        """Advance in-transit trucks by minutes; arrive when remaining is exhausted."""
        still = {}
        for truck, (source, destination, remaining) in self.in_transit.items():
            left = remaining - minutes
            if left <= 0:
                self._arrive(truck, source, destination)
            else:
                still[truck] = (source, destination, left)
        self.in_transit = still

    def _execute_demand_shortcut(self, action):
        """Legacy multi-segment haul when every movement is an open demand arc.

        Trucks stay at the source (round-trip haul). Used so large fleets remain
        searchable; repositioning still uses the in-transit clock model.
        """
        groups = defaultdict(list)
        for movement in action.movements:
            k = (movement.source, movement.destination)
            groups[k].append(movement.truck)

        remaining_demand = {
            k: (self.route_demands[k] - self.covered_demands[k]) for k in groups
        }
        candidate_segment_amounts = [self.max_segment - self.segment]
        for k in groups:
            trucks = groups[k]
            capacity = float(sum(t.tonnage_capacity for t in trucks))
            candidate_segment_amounts.append(
                math.ceil(remaining_demand[k] / capacity)
            )

        num_segments = min(candidate_segment_amounts)
        for k in groups:
            trucks = groups[k]
            capacity = float(sum(t.tonnage_capacity for t in trucks))
            self.covered_demands[k] += min(
                remaining_demand[k], capacity * num_segments
            )
            arc_minutes = self.config.travel_time(k[0], k[1])
            self.trips += len(trucks) * num_segments * arc_minutes

        self.segment += num_segments
        self.clock_minutes += num_segments * self.segment_length_minutes
        if self.in_transit:
            self._progress_transit(num_segments * self.segment_length_minutes)

    def execute_action(self, action):
        """Apply movements and advance the clock.

        Repositioning uses per-segment in-transit tracking. An all-demand action
        may still use the multi-segment haul shortcut so the toy mine stays
        solvable.
        """

        demand_only = len(action.movements) > 0
        if demand_only:
            for m in action.movements:
                key = (m.source, m.destination)
                if (
                    key not in self.route_demands
                    or self.covered_demands[key] >= self.route_demands[key]
                ):
                    demand_only = False
                    break

        if demand_only:
            self._execute_demand_shortcut(action)
            return

        for movement in action.movements:
            truck, source, destination = (
                movement.truck,
                movement.source,
                movement.destination,
            )
            if truck in self.in_transit:
                continue
            if truck not in self.resident_trucks[source]:
                continue

            travel = self.config.travel_time(source, destination)
            self.trips += travel
            self.resident_trucks[source].remove(truck)
            self.in_transit[truck] = (source, destination, travel)

        # One segment elapses: clock advances by shift minutes / segment count
        self.segment += 1
        self.clock_minutes += self.segment_length_minutes
        self._progress_transit(self.segment_length_minutes)


class Movement(object):
    """ Represents the movement of a truck from where it currently is to another location on the mine """

    def __init__(self, truck, source, destination):
        """ Represents a movement that will be executed in an action """
        self.truck = truck
        self.source = source
        self.destination = destination

    def __repr__(self):
        return "Move %s from %s to %s" % (self.truck, self.source, self.destination)

    def __str__(self):
        return repr(self)

    def __hash__(self):
        return hash((self.truck, self.source, self.destination))

    def __eq__(self, other):
        return hash(self) == hash(other)


class Action(object):
    """ Encodes the action to be taken as a series of movements """

    def __init__(self, *movements):
        """ Keeps track of the movements that will happen during this action """
        self.movements = movements

    def __hash__(self):
        capacities = defaultdict(list)
        for m in self.movements:
            src, dst, truck = m.source, m.destination, m.truck
            capacities[(src, dst)].append(truck)

        elements = frozenset((k[0], k[1], len(v), sum(t.tonnage_capacity for t in v)) for k, v in capacities.items())
        return hash(elements)

    def __eq__(self, other):
        return hash(self) == hash(other)
