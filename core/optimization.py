""" Contains all the elements related to the optimization via MLP """

import math
import itertools as it
from pulp import *


class LinearProblem(object):
    """ Represents an instance of a subproblem to be solved by the fleet optimizator"""

    def __init__(self, name, fleet_size, travel_time_minutes, shift_length_hours):
        """ Constructor.

        name: (source, destination) arc endpoints
        fleet_size: maximum trucks available in a segment
        travel_time_minutes: travel time for this arc
        shift_length_hours: scenario shift length; segment count is
            ceil(shift_length_hours * 60 / travel_time_minutes)
        """
        self.name = name
        self.fleet_size = fleet_size
        self.travel_time_minutes = float(travel_time_minutes)
        self.shift_length_hours = float(shift_length_hours)

        if not isinstance(name, (tuple, list)) or len(name) != 2:
            raise ValueError("arc name must be a (source, destination) pair, got %r" % (name,))

        source, destination = name
        self.locations = (source, destination)

        if self.travel_time_minutes <= 0:
            raise ValueError(
                "travel_time_minutes must be positive for destination %s" % (destination,)
            )
        if self.shift_length_hours <= 0:
            raise ValueError("shift_length_hours must be positive")

        self.num_segments = int(
            math.ceil(self.shift_length_hours * 60.0 / self.travel_time_minutes)
        )


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
