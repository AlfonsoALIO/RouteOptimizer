"""Story 1.2: same fleet at different segments are distinct search states."""

from collections import OrderedDict

from core_search.entities import Location, MineConfiguration, Truck
from core_search.search import Node
from core_search.state import FleetState


def _small_fleet():
    garage = Location("garage", 2)
    shovel = Location("S1", 2)
    crusher = Location("C", 2)
    config = MineConfiguration(
        [
            (garage, shovel),
            (shovel, garage),
            (shovel, crusher),
            (crusher, shovel),
            (crusher, garage),
        ]
    )
    trucks = [Truck("truck_1", 100), Truck("truck_2", 100)]
    demands = OrderedDict([((shovel, crusher), 200)])
    return FleetState(config, trucks, demands, max_segment=10)


def test_different_segments_are_not_equal_and_hash_differs():
    early = _small_fleet()
    later = early.clone()
    later.segment = early.segment + 3

    assert early.covered_demands == later.covered_demands
    assert early.resident_trucks.keys() == later.resident_trucks.keys()
    for loc in early.resident_trucks:
        assert early.resident_trucks[loc] == later.resident_trucks[loc]
    assert early != later
    assert hash(early) != hash(later)


def test_same_segment_same_coverage_and_residents_are_equal():
    a = _small_fleet()
    b = a.clone()

    assert a.segment == b.segment
    assert a == b
    assert hash(a) == hash(b)


def test_equality_compares_fields_not_hash_alone():
    """Equality checks segment, coverage, and residents; not hash equality."""
    a = _small_fleet()
    b = a.clone()
    assert a == b
    assert a != "not-a-fleet-state"
    assert (a == None) is False

    later = a.clone()
    later.segment = a.segment + 1
    assert later != a


def test_astar_treats_different_segments_as_different_nodes():
    early = _small_fleet()
    later = early.clone()
    later.segment = early.segment + 1

    n_early = Node(early, cost=1)
    n_later = Node(later, cost=2)

    assert n_early != n_later
    assert hash(n_early) != hash(n_later)

    explored = {n_early}
    assert n_later not in explored

    queue = [(n_early.cost, n_early)]
    assert n_later not in [e[1] for e in queue]
