""" Module file for Core """
import json
from pulp import LpStatus


class Parameters(object):
    """User-provided shift horizon and tonnage demand for the batch flow."""

    def __init__(self, tonnage_demand, shift_length, num_segments=None):
        if tonnage_demand is None:
            raise ValueError("missing required field: tonnage_demand")
        if shift_length is None:
            raise ValueError("missing required field: shift_length")
        self.tonnage_demand = tonnage_demand
        self.shift_length = float(shift_length)
        if self.shift_length <= 0:
            raise ValueError("shift_length must be positive")
        self.num_segments = None if num_segments is None else int(num_segments)
        if self.num_segments is not None and self.num_segments <= 0:
            raise ValueError("num_segments must be positive")



def calculate_route_times(frame):
    """ Computes the average time in a route per truck by using the data """


    # Group by destination TODO: Add source to this filtering, verify the validity of this grouping
    grouped = frame.groupby("destination")

    # Compute the micro average time for each destination
    averages = dict()
    for k, v in grouped:
        avg_time = (60/(v.loads/v.haul_time)).mean()
        averages[k] = avg_time

    return dict(averages)


def _variables_to_jsonable(variables):
    """Serialize PuLP variable maps, including nested mine-flow structures."""
    if isinstance(variables, dict):
        out = {}
        for key, val in variables.items():
            label = key if isinstance(key, str) else str(key)
            out[label] = _variables_to_jsonable(val)
        return out
    if isinstance(variables, (list, tuple)):
        # List of LpVariable
        if variables and hasattr(variables[0], "name"):
            return {a.name: a.value() for a in variables}
        return [_variables_to_jsonable(v) for v in variables]
    if hasattr(variables, "name") and hasattr(variables, "value"):
        return {variables.name: variables.value()}
    return variables


class ProblemResults(object):
    """ Represents the result of a LP problem """
    def __init__(self, status, variables):
        self.status = status
        self.variables = variables

    def to_json(self):
        x = dict()

        x['status'] = LpStatus[self.status]
        x['variables'] = _variables_to_jsonable(self.variables)

        jstring = json.dumps(x)

        return jstring
