"""Story 1.1: cheaper waiting open-set assignments replace worse ones."""

from core_search.search import AStar, Node, enqueue_or_decrease


class _Action(object):
    def __init__(self, name, next_label, trip_cost):
        self.name = name
        self.next_label = next_label
        self.trip_cost = trip_cost


class GraphState(object):
    """Minimal search state: labeled graph with additive trip cost.

    Supports the A* surface used by FleetState (trips, segment,
    total_covered_demand, clone, possible_actions, execute_action,
    is_successful) without depending on the mine model.
    """

    def __init__(self, label, edges, goal, trips=0, segment=1):
        # edges: label -> list of (action_name, next_label, trip_cost)
        self.label = label
        self.edges = edges
        self.goal = goal
        self.trips = trips
        self.segment = segment

    def __eq__(self, other):
        return isinstance(other, GraphState) and self.label == other.label

    def __hash__(self):
        return hash(self.label)

    def clone(self):
        return GraphState(self.label, self.edges, self.goal, self.trips, self.segment)

    def possible_actions(self):
        return [
            _Action(name, nxt, cost) for name, nxt, cost in self.edges.get(self.label, [])
        ]

    def execute_action(self, action):
        self.label = action.next_label
        self.trips += action.trip_cost
        self.segment += 1

    def is_successful(self):
        return self.label == self.goal

    def total_covered_demand(self):
        return 0


def _two_paths_to_goal(expensive_first=True):
    """Start reaches Goal by an expensive path and a cheap path.

    When expensive_first is True, possible_actions yields the worse
    path first so the open set queues the expensive Goal before the cheap one.
    """
    expensive = ("expensive", "goal", 100)
    cheap = ("cheap", "goal", 1)
    start_edges = [expensive, cheap] if expensive_first else [cheap, expensive]
    edges = {
        "start": start_edges,
        "goal": [],
    }
    return GraphState("start", edges, goal="goal")


def _goal_node(cost, action_name):
    state = GraphState("goal", {"goal": []}, goal="goal", trips=cost)
    return Node(state, cost, _Action(action_name, "goal", cost))


def test_cheaper_waiting_goal_replaces_worse_and_is_returned():
    """Worse Goal is queued first; cheaper copy replaces it; solve returns cost 1."""
    searcher = AStar(_two_paths_to_goal(expensive_first=True))
    solution = searcher.solve()

    assert solution is not None
    assert solution.cost == 1
    assert solution.action.name == "cheap"
    assert solution.state.label == "goal"


def test_equal_or_higher_cost_leaves_waiting_entry():
    """A second path that is not cheaper must not replace the waiting node."""
    edges = {
        "start": [("to_mid", "mid", 1)],
        "mid": [
            ("cheap_goal", "goal", 1),
            ("expensive_goal", "goal", 50),
        ],
        "goal": [],
    }
    searcher = AStar(GraphState("start", edges, goal="goal"))
    solution = searcher.solve()

    assert solution is not None
    assert solution.cost == 2  # 1 (to mid) + 1 (cheap_goal)
    assert solution.action.name == "cheap_goal"


def test_enqueue_decrease_stores_cost_node_pair():
    """Waiting slot becomes (cost, node), not a bare node."""
    queue = []
    worse = _goal_node(100, "expensive")
    better = _goal_node(1, "cheap")

    assert enqueue_or_decrease(queue, worse) == "pushed"
    assert enqueue_or_decrease(queue, better) == "decreased"

    assert len(queue) == 1
    entry = queue[0]
    assert isinstance(entry, tuple)
    assert len(entry) == 2
    cost, node = entry
    assert cost == 1
    assert node is better
    assert node.cost == 1


def test_enqueue_leaves_equal_or_higher_cost_unchanged():
    queue = []
    first = _goal_node(5, "first")
    equal = _goal_node(5, "equal")
    worse = _goal_node(9, "worse")

    assert enqueue_or_decrease(queue, first) == "pushed"
    assert enqueue_or_decrease(queue, equal) == "unchanged"
    assert enqueue_or_decrease(queue, worse) == "unchanged"

    assert len(queue) == 1
    cost, node = queue[0]
    assert cost == 5
    assert node is first


def test_solve_returns_cheaper_node_when_it_is_best_goal():
    """Regression: without decrease-key, expensive-first order returned cost 100."""
    solution = AStar(_two_paths_to_goal(expensive_first=True)).solve()
    assert solution.cost == 1
