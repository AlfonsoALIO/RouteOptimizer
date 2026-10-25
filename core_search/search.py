""" This file contains an implementation of search algorithms """
import sys, heapq


class Node(object):
    """ Node of a search tree """
    def __init__(self, state, cost = 0, action=None, parent = None):
        """ Fields: parent is a reference to the node's parent in the tree
                    state is a FleetState instance
                    cost is path travel time in minutes (plus heuristic when ranking)
                    action is the  action instance that resulted in state as its outcome"""

        self.parent = parent
        self.cost = cost
        self.action = action
        self.state = state

    def __eq__(self, other):
        """ Only consider the state for comparisons"""
        return self.state == other.state

    def __lt__(self, other):
        return self.cost < other.cost

    def __le__(self, other):
        return self.cost <= other.cost

    def __hash__(self):
        """ Similarly, only use the state's hash as the node's hash """
        return hash(self.state)

    def path_from_root(self):
        """ Returns the path from the root to the current node"""
        reversed_path = [self]

        current = self
        while current.parent:
            current = current.parent
            reversed_path.insert(0, current)

        return reversed_path


def enqueue_or_decrease(queue, child):
    """Push child onto the open set, or replace a waiting copy if cheaper.

    Every open-set entry is a ``(cost, node)`` pair. A waiting node with
    equal or higher cost is left unchanged.
    """
    waiting_index = None
    for ix, (_, waiting) in enumerate(queue):
        if waiting == child:
            waiting_index = ix
            break

    if waiting_index is None:
        heapq.heappush(queue, (child.cost, child))
        return "pushed"

    if child.cost < queue[waiting_index][1].cost:
        queue[waiting_index] = (child.cost, child)
        heapq.heapify(queue)
        return "decreased"

    return "unchanged"


class AStar(object):

    def __init__(self, initial_state, heuristic = lambda s: 0, listener = None):
        """ Parameters: initial_state: First step of the search """
        self.initial_state = initial_state
        self.heuristic = heuristic
        self.best = None
        self.saturation = 0.0
        self.listener = listener

    def solve(self):
        """ Does a Uniform Cost Search and returns a reference to a node containing an optimal solution """

        # Root of the search tree
        root = Node(self.initial_state)

        # Cache of explored nodes
        explored = set()

        # Priority queue for the nodes to explore
        queue = list()

        # Add the initial state to the priority queue
        heapq.heappush(queue, (root.cost, root))

        # Reference to the solution, currently empty
        solution = None

        # Number of iterations
        num = 0

        # Main loop of UCS
        while solution is None and len(queue) > 0:
            num += 1

            # Fetch the next node to consider
            _, node = heapq.heappop(queue)  # Ignore the first element of the tuple, which is the cost used for ranking

            # A stale higher-cost copy may remain after a decrease-key; skip it
            if node in explored:
                continue

            if self.listener:
                self.listener((num, node.cost, node.state.trips, node.state.segment, node.state.total_covered_demand()))

            # Add it to the explored cache
            explored.add(node)
            # Reference to the state
            state = node.state

            # If this is a successful state, bingo!
            if state.is_successful():
                # Keep track of the solution
                solution = node
            # Otherwise, expand the fringe of the search
            else:
                # Compute the possible children
                possible_actions = state.possible_actions()
                for action in possible_actions:
                    # Clone the state
                    new_state = state.clone()
                    # Execute the given action to mutate the clone
                    new_state.execute_action(action)
                    # Create the child node
                    child = Node(new_state, new_state.trips + self.heuristic(new_state), action, node)

                    if child.cost >= sys.maxsize:
                        continue

                    # Already expanded: do not reopen
                    if child in explored:
                        continue

                    enqueue_or_decrease(queue, child)

        # Return the solution, if found
        return solution
