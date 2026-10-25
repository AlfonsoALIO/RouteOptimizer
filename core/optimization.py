""" Contains all the elements related to the optimization via MLP """

import math
import itertools as it
from pulp import *


class LinearProblem(object):
    """ Represents an instance of a subproblem to be solved by the fleet optimizator"""

    def __init__(self, name, arc_times, fleet_size):
        """ Constructor.

        name: (source, destination) arc endpoints
        arc_times: map of destination -> travel time used for the horizon
        fleet_size: maximum trucks available in a segment
        """
        self.name = name
        self.arc_times = arc_times
        self.fleet_size = fleet_size

        if not isinstance(name, (tuple, list)) or len(name) != 2:
            raise ValueError("arc name must be a (source, destination) pair, got %r" % (name,))

        source, destination = name
        self.locations = (source, destination)

        if destination not in arc_times:
            raise ValueError("missing destination travel time: %s" % (destination,))

        # TODO: Parameterize this
        # Ten hours and two shifts
        self.num_segments = math.ceil(10 * 60 * 2 / float(arc_times[destination]))


def solve(problem):
    """ Core of the fleet optimization algorithm. Runs the MLP for the particular subproblem
        Returns the assignment and the optimized target
    """

    # Instance of the problem
    instance = LpProblem("Fleet Optimizer", LpMinimize)

    # Variables keyed by arc endpoints (locations)
    X = dict()
    for i in problem.locations:
        X[i] = list()
        for j in range(problem.num_segments):
            x = LpVariable("X_%s_%i" % (i, j), lowBound=0, cat=LpInteger)
            X[i].append(x)

    # The target function
    target = LpAffineExpression([(x, 1) for x in it.chain.from_iterable(X.values())])
    instance += target


    # Constraints

    # Tonnage Demand
    #######################################################
    # TODO: Paremeterize this
    T = dict()
    for i in problem.locations:
        T[i] = list()
        for j in range(problem.num_segments):
            t = 1
            T[i].append(t)
    #######################################################

    C = 100 # TODO: Parameterize this

    for i in problem.locations:
        for j in range(problem.num_segments):
            tc = C*X[i][j] >= T[i][j]
            instance += tc

    # Fleet size
    for j in range(problem.num_segments):
        elements = [(X[i][j], 1) for i in problem.locations]
        expr = LpAffineExpression(elements)
        instance += LpConstraint(expr, LpConstraintLE, "Fleet_conservation_%i" % j, problem.fleet_size)

    #instance.writeLP("test.lp")
    status = instance.solve(PULP_CBC_CMD(msg=0))
    return status, X
