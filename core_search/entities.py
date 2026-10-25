""" Entities related to a decision process for UCS or A* """
from collections import defaultdict


class Truck(object):
    """Represents a car, with its properties, that will circulate throughout the mine"""
    def __init__(self, name, tonnage_capacity):
        """Properties: Name of the car, tonnage capacity of this car"""
        self.name = name
        self.tonnage_capacity = tonnage_capacity

    def __repr__(self):
        """Human-friendly representation of the current instance"""
        return "Truck name: %s - Capacity: %i tons" % (self.name, self.tonnage_capacity)


    def __hash__(self):
        """A car is uniquely identified by its name"""
        return hash(self.name)


class Location(object):
    """Location at the mine and its properties"""
    def __init__(self, name, resident_capacity):
        """Properties: Name of the location and resident fleet capacity"""
        self.name = name
        self.resident_capacity = resident_capacity

    def __repr__(self):
        return "Location name: %s - Queue capacity: %i trucks" % (self.name, self.resident_capacity)

    def __hash__(self):
        """A car is uniquely identified by its name"""
        return hash(self.name)

    def __eq__(self, other):
        tp = type(other)
        if tp == str:
            return self.name == other
        elif tp == Location:
            return self.name == other.name
        else:
            return False


class MineConfiguration(object):
    """Represents the arrangement of the mine as a graph connecting the locations.
    This class represents a graph representation of the mine"""
    def __init__(self, connections, travel_times=None):
        """Connections is a list of the directed edges of the graph. The nodes are inferred from the pairs.

        travel_times: optional map (src, dest) -> minutes. Missing arcs default to 1 minute.
        """

        # Store the raw edges
        self._connections = tuple(connections)

        self._locations = set()

        outgoing = defaultdict(list) # Incidence list, where the key is a location and the value is an incidence list of the key

        # Build the outgoing incidence lists. This structure is considered immutable after consruction
        for src, dest in connections:
            outgoing[src].append(dest)
            # Piggyback the loop to build the locations set
            self._locations.add(src)
            self._locations.add(dest)

        self.outgoing = outgoing

        incoming = defaultdict(list)
        # Build the incoming incidence lists. This structure is considered immutable after consruction
        for src, dest in connections:
            incoming[dest].append(src)

        self.incoming = incoming
        self._travel_times = dict(travel_times) if travel_times else {}

    def travel_time(self, source, destination):
        """Return arc travel time in minutes (default 1 if unset)."""
        return float(self._travel_times.get((source, destination), 1.0))

    def destinations(self, source):
        """Returns the locations to which a car can go from the current location"""
        return self.outgoing[source]

    def incoming(self, dest):
        """Returns the locations to which a car could've come to the current location"""
        return self.incoming[dest]

    def locations(self):
        """Returns the set of locations in the configuration"""
        return self._locations

    def __hash__(self):
        """Characterize the configuration by its connections"""
        return hash(self._connections)