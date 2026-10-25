"""State representation of the mine"""

import copy
import itertools as it
import math
from collections import defaultdict


class FleetState(object):
    """ Represents the current status of the fleet """

    def __init__(self, config, trucks, route_demands, max_segment, warm_start=False):
        """ Parameters:
                - config: MineConfiguration instance
                - truck_capacities: Map from truck name to tonnage capacity.
                    Fleet members are inferred from this parameter
                - route_demands: Map key: Tuple of locations,
        """

        self.config = config
        self.trucks = trucks
        self.route_demands = route_demands

        self.max_segment = max_segment

        if not warm_start:
            # Internal book keeping of the state
            self.trips = 0
            self.covered_demands = {k: 0 for k in route_demands}
            self.resident_trucks = {loc: set() for loc in config.locations()}
            self.segment = 1

            self.garage = list(filter(lambda l: l.name == "garage", config.locations()))[0]

            # Assume all trucks are on the garage
            for t in self.trucks:
                self.resident_trucks[self.garage].add(t)

            # Used for the heuristic computation
            self.max_capacity = max(t.tonnage_capacity for t in trucks)
            self.num_effective_routes = sum(d.resident_capacity for s, d in route_demands)

    def __eq__(self, other):
        """ Compares covered demand, resident assignments, and segment """
        if not isinstance(other, FleetState):
            return False
        return (
            self.segment == other.segment
            and frozenset(self.covered_demands.items()) == frozenset(other.covered_demands.items())
            and self.__factorize_assignments() == other.__factorize_assignments()
        )

    def __hash__(self):
        """ Custom hash implementation to consider only elements of interest """

        elements = (
            self.segment,
            frozenset(self.covered_demands.items()),
            self.__factorize_assignments(),
        )

        return hash(elements)

    def __factorize_assignments(self):
        """ This is a helper method to compute the hash of the state """

        # Generate tuples for the resident truck configurations of the following format:
        # (location, # of trucks, total capacity)
        return frozenset((k, len(v), sum(t.tonnage_capacity for t in v)) for k, v in self.resident_trucks.items())

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
        cl = FleetState(self.config, self.trucks, self.route_demands, self.max_segment, warm_start=True)
        cl.covered_demands = {k: v for k, v in self.covered_demands.items()}
        cl.resident_trucks = {k: copy.copy(v) for k, v in self.resident_trucks.items()}
        cl.trucks = self.trucks  # No need to copy this as it's immutable
        cl.trips = self.trips
        cl.segment = self.segment
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

    def possible_actions(self):
        """ Returns an iterable with all the actions to consider given the current state """

        # If time's up, no actions left
        if self.segment >= self.max_segment:
            return list()

        movement_list = list()
        config = self.config

        # First, figure out the locations in the mine that have any truck
        rt = self.resident_trucks
        locations = sorted([l for l in rt if len(rt[l]) > 0], key=lambda l: l.name)

        for src in locations:
            # What are the possible destinations, only consider those with enough room
            # Compute how many trucks we can move at most

            ds = sorted(config.destinations(src), key=lambda l: l.name)

            # Fetch the trucks of the current destination, sorted decreasingly by capacity
            local_trucks = sorted(self.resident_trucks[src], key=lambda tr: tr.tonnage_capacity, reverse=True)

            # Categorize the destinations reachable from the current location
            destinations_with_demand = list()
            destinations_without_demand = list()
            for d in ds:
                if (src, d) in self.route_demands:
                    destinations_with_demand.append(d)
                else:
                    destinations_without_demand.append(d)

            # If the pair has demand
            for d in destinations_with_demand:
                key = (src, d)

                # If there's still demand to cover in this route
                if self.covered_demands[key] < self.route_demands[key]:
                    remaining_demand = self.route_demands[key] - self.covered_demands[key]
                    # For each of slots available in the destination, dispatch a truck, if still available
                    for i in range(d.resident_capacity):
                        # The truck will be dispatched only if there's still demand to cover and if we haven't used
                        # them all yet
                        if remaining_demand > 0 and len(local_trucks) > 0:
                            t = local_trucks.pop()
                            movement_list.append(Movement(t, src, d))
                            remaining_demand -= t.tonnage_capacity
                        # Otherwise we will break the loop, as it doesn't make sense anymore
                        else:
                            break

            # Get a list of eligible destinations to dispatch by looking to the second order destinations
            eligible_ds = list()
            for d in destinations_without_demand:
                for d2 in config.destinations(d):
                    key = (d, d2)
                    if key in self.route_demands:
                        remaining_demand = self.route_demands[key] - self.covered_demands[key]
                        if remaining_demand > 0:
                            eligible_ds.append(d)
                            break

            # Here do something with the eligible destinations
            for d in eligible_ds:
                # If there are trucks left to dispatch
                if len(local_trucks) > 0:
                    # How many trucks could be dispatched to the destination
                    num_slots = d.resident_capacity - len(self.resident_trucks[d])
                    # Dispatch those trucks
                    for i in range(num_slots):
                        t = local_trucks.pop()
                        movement_list.append(Movement(t, src, d))
                # If there are no trucks left, break this loop since it doesn't make sense anymore
                else:
                    break

            # If there are trucks left here and no more eligible destinations, send them back to the garage
            # As long as this isn't the garage
            if src != self.garage:
                for t in local_trucks:
                    movement_list.append(Movement(t, src, self.garage))

        return [Action(*movement_list), Action()]

    def execute_action(self, action):
        """ Actual implementation of execute action that mutates an instance of FleetState
            This function is not meant to be called directly, but by the instance method defined above """

        # Figure out if all the movements are on a route with demand
        shortcut = True if len(action.movements) > 0 else False

        for m in action.movements:
            s, d = (m.source, m.destination)
            # If one of the movements is to a route without demand, then we can't do the shortcut
            if (s, d) not in self.route_demands:
                shortcut = False
                break
            # Also, if it is in a route with demand but it's already satisfied, can't do the shortcut
            elif self.covered_demands[(s, d)] >= self.route_demands[(s, d)]:
                shortcut = False
                break

        # If we can't do the shortcut, only simulate one time segment
        if not shortcut:
            # Increase the segment by one
            self.segment += 1

            # Iterate over each movement of the action
            for movement in action.movements:
                # Unpack the elements of the movement
                truck, source, destination = movement.truck, movement.source, movement.destination
                # Increment the trip counter for this truck that was reassigned
                self.trips += 1

                # If the destination is the endpoint of a route, don't change the location of the current truck,
                # as the outcome of the action represents a round-trip from source to destination
                if not (source, destination) in self.route_demands:
                    # Change the location of truck on the fleet state
                    self.resident_trucks[source].remove(truck)
                    self.resident_trucks[destination].add(truck)

                # If it is, then we decrement the remaining demand to be covered
                else:
                    # Fetch the capacity of the truck
                    capacity = truck.tonnage_capacity
                    # Compute the remaining capacity
                    remaining = self.route_demands[(source, destination)] - self.covered_demands[(source, destination)]
                    # Increment the covered demand by the capacity or the remaining capacity
                    self.covered_demands[(source, destination)] += min(capacity, remaining)

        # This is the shortcut
        else:
            # Group the trucks to travel a route
            groups = defaultdict(list)
            for movement in action.movements:
                truck, source, destination = movement.truck, movement.source, movement.destination
                k = (source, destination)
                groups[k].append(truck)

            # Compute the remaining demand on each group
            remaining_demand = {k: (self.route_demands[k] - self.covered_demands[k]) for k in groups}

            # Figure out how many segments we can execute on this iteration
            # The first candidate value is the remaining number of segments
            candidate_segment_amounts = [self.max_segment - self.segment]
            # Figure out how many segments can be executed for each group using the current subfleet assigned on each
            for k in groups:
                trucks = groups[k]
                remaining = remaining_demand[k]
                capacity = float(sum(t.tonnage_capacity for t in trucks))
                segments = math.ceil(remaining / capacity)
                # Add the amount of segments required to cover the demand of this route to the candidate pool
                candidate_segment_amounts.append(segments)

            # The actual number of segments to be simulated is the minimum of the pool
            num_segments = min(candidate_segment_amounts)

            # Simulate num_segments segments for each of the routes
            for k in groups:
                trucks = groups[k]
                capacity = float(sum(t.tonnage_capacity for t in trucks))
                self.covered_demands[k] += min(remaining_demand[k], (capacity * num_segments))
                self.trips += (len(trucks) * num_segments)

            # Finally, increase the segment counter by the chosen amount of segments that were simulated
            self.segment += num_segments


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
