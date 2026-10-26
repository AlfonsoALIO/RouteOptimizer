"""Learned dispatch policy: a small MLP that imitates A* action choices.

The network scores each legal action. It does not prove optimality. The A*
search and the MILP solver remain the source of a proven plan.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from core_search.run import _heuristic

FEATURE_NAMES = (
    "segment_frac",
    "demand_remaining_frac",
    "trucks_in_garage_frac",
    "trucks_in_transit_frac",
    "heuristic_shift_frac",
    "open_routes_frac",
    "action_is_idle",
    "movements_per_truck",
    "demand_move_frac",
    "to_garage_frac",
    "from_garage_frac",
    "travel_shift_frac",
    "destination_frac",
)

HIDDEN = (16, 8)
PACKAGE_DIR = Path(__file__).resolve().parent
DEFAULT_WEIGHTS = PACKAGE_DIR / "dispatch_policy_weights.npz"
DEFAULT_CONFIG = PACKAGE_DIR / "dispatch_policy_config.json"


def action_features(state, action):
    """Fixed-length features for one legal action in a fleet state."""
    fleet = max(len(state.trucks), 1)
    shift_min = max(float(state.shift_length_hours) * 60.0, 1.0)
    total_demand = sum(float(v) for v in state.route_demands.values()) or 1.0
    covered = float(state.total_covered_demand())
    open_routes = sum(
        1
        for key, tons in state.route_demands.items()
        if state.covered_demands[key] < tons
    )
    locations = list(state.config.locations())
    moves = list(action.movements)
    n_moves = len(moves)
    demand_moves = 0
    to_garage = 0
    from_garage = 0
    travel = 0.0
    dests = set()
    for move in moves:
        dests.add(move.destination.name)
        if move.destination.name == "garage":
            to_garage += 1
        if move.source.name == "garage":
            from_garage += 1
        key = (move.source, move.destination)
        if key in state.route_demands and state.covered_demands[key] < state.route_demands[key]:
            demand_moves += 1
        travel += float(state.config.travel_time(move.source, move.destination))

    return np.asarray(
        [
            float(state.segment) / max(float(state.max_segment), 1.0),
            max(0.0, 1.0 - covered / total_demand),
            len(state.resident_trucks[state.garage]) / fleet,
            len(state.in_transit) / fleet,
            min(float(_heuristic(state)) / shift_min, 5.0),
            min(open_routes / 4.0, 1.0),
            1.0 if n_moves == 0 else 0.0,
            n_moves / fleet,
            (demand_moves / n_moves) if n_moves else 0.0,
            (to_garage / n_moves) if n_moves else 0.0,
            (from_garage / n_moves) if n_moves else 0.0,
            min(travel / shift_min, 5.0),
            len(dests) / max(len(locations), 1),
        ],
        dtype=np.float64,
    )


def _relu(x):
    return np.maximum(x, 0.0)


def _sigmoid(x):
    return 1.0 / (1.0 + np.exp(-np.clip(x, -40.0, 40.0)))


class DispatchPolicy(object):
    """MLP action scorer. ``weights`` maps layer index to (W, b)."""

    def __init__(self, weights, mean, std):
        self.weights = weights
        self.mean = np.asarray(mean, dtype=np.float64)
        self.std = np.asarray(std, dtype=np.float64)
        self.std = np.where(self.std < 1e-8, 1.0, self.std)

    def score_features(self, features):
        x = (np.asarray(features, dtype=np.float64) - self.mean) / self.std
        for index, (matrix, bias) in enumerate(self.weights):
            x = x @ matrix + bias
            if index < len(self.weights) - 1:
                x = _relu(x)
        return float(_sigmoid(x).reshape(-1)[0])

    def score(self, state, action):
        return self.score_features(action_features(state, action))

    def choose(self, state):
        """Return the highest-scoring legal action, or None if there are none."""
        actions = list(state.possible_actions())
        if not actions:
            return None
        best = max(actions, key=lambda action: self.score(state, action))
        return best

    def save(self, weights_path, config_path, metadata):
        arrays = {"mean": self.mean, "std": self.std, "n_layers": np.asarray([len(self.weights)])}
        for index, (matrix, bias) in enumerate(self.weights):
            arrays["W%d" % index] = matrix
            arrays["b%d" % index] = bias
        np.savez(weights_path, **arrays)
        config = dict(metadata)
        config["feature_names"] = list(FEATURE_NAMES)
        config["hidden"] = list(HIDDEN)
        Path(config_path).write_text(json.dumps(config, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_policy(weights_path=None):
    path = Path(weights_path or DEFAULT_WEIGHTS)
    data = np.load(path)
    n_layers = int(data["n_layers"][0])
    weights = [(data["W%d" % i], data["b%d" % i]) for i in range(n_layers)]
    return DispatchPolicy(weights, data["mean"], data["std"])


def train_policy(features, labels, seed=0, steps=400, lr=0.01):
    """Train the MLP. ``features`` is (N, D), ``labels`` is (N,) in {0, 1}."""
    rng = np.random.default_rng(seed)
    x = np.asarray(features, dtype=np.float64)
    y = np.asarray(labels, dtype=np.float64).reshape(-1, 1)
    mean = x.mean(axis=0)
    std = x.std(axis=0)
    std = np.where(std < 1e-8, 1.0, std)
    xn = (x - mean) / std

    sizes = (xn.shape[1],) + HIDDEN + (1,)
    weights = []
    moment_m = []
    moment_v = []
    for n_in, n_out in zip(sizes[:-1], sizes[1:]):
        matrix = rng.normal(0.0, np.sqrt(2.0 / n_in), size=(n_in, n_out))
        bias = np.zeros(n_out)
        weights.append([matrix, bias])
        moment_m.append([np.zeros_like(matrix), np.zeros_like(bias)])
        moment_v.append([np.zeros_like(matrix), np.zeros_like(bias)])

    pos = max(float(y.sum()), 1.0)
    neg = max(float(len(y) - float(y.sum())), 1.0)
    pos_weight = neg / pos
    beta1, beta2, eps = 0.9, 0.999, 1e-8

    for step in range(1, steps + 1):
        h = xn
        caches = []
        for index, (matrix, bias) in enumerate(weights):
            z = h @ matrix + bias
            caches.append((h, z))
            h = z if index == len(weights) - 1 else _relu(z)
        pred = _sigmoid(h)
        # dL/dz for weighted BCE
        weight = np.where(y > 0.5, pos_weight, 1.0)
        delta = weight * (pred - y) / max(len(y), 1)

        for index in reversed(range(len(weights))):
            h_in, z = caches[index]
            if index < len(weights) - 1:
                delta = delta * (z > 0)
            grad_w = h_in.T @ delta
            grad_b = delta.sum(axis=0)
            delta = delta @ weights[index][0].T
            for param_i, grad in enumerate((grad_w, grad_b)):
                moment_m[index][param_i] = beta1 * moment_m[index][param_i] + (1 - beta1) * grad
                moment_v[index][param_i] = beta2 * moment_v[index][param_i] + (1 - beta2) * (grad * grad)
                m_hat = moment_m[index][param_i] / (1 - beta1**step)
                v_hat = moment_v[index][param_i] / (1 - beta2**step)
                weights[index][param_i] -= lr * m_hat / (np.sqrt(v_hat) + eps)

    packed = [(matrix, bias) for matrix, bias in weights]
    return DispatchPolicy(packed, mean, std)
