#!/usr/bin/env python3
"""Train the dispatch-policy MLP on A* traces and write the checkpoint."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.scenario import load_scenario  # noqa: E402
from core.synthetic import (  # noqa: E402
    ore_waste_scenario,
    shuttle_scenario,
    two_shovel_scenario,
)
from core_search.run import run as run_dispatch  # noqa: E402
from route_optimizer.policy import (  # noqa: E402
    DEFAULT_CONFIG,
    DEFAULT_WEIGHTS,
    FEATURE_NAMES,
    action_features,
    train_policy,
)

HUB_DIR = ROOT / "huggingface" / "dispatch_policy"


def training_scenarios():
    """Small synthetic mines. Every 5th scenario is held out."""
    rows = []
    index = 0
    for fleet in (2, 3, 4):
        for tons in (50.0, 100.0, 150.0, 200.0, 300.0):
            for travel in (10.0, 15.0, 20.0):
                for shift in (1.0, 2.0):
                    payload = shuttle_scenario(fleet, 100.0, travel, shift, tons, 2)
                    rows.append(("shuttle", index, payload, index % 5 == 0))
                    index += 1
    for fleet in (2, 3, 4):
        for tons in (100.0, 200.0):
            for travel in (15.0, 20.0):
                payload = two_shovel_scenario(fleet, 100.0, travel, 2.0, tons, 2)
                rows.append(("two_shovel", index, payload, index % 5 == 0))
                index += 1
    for fleet in (2, 3):
        for tons in (80.0, 150.0):
            payload = ore_waste_scenario(fleet, 100.0, 15.0, 2.0, tons, 2)
            rows.append(("ore_waste", index, payload, index % 5 == 0))
            index += 1
    return rows


def decision_accuracy(policy, decisions):
    """Fraction of states where the top-scored action is the solver's action."""
    if not decisions:
        return 0.0
    correct = 0
    for features_rows, labels in decisions:
        scores = [policy.score_features(row) for row in features_rows]
        pick = int(np.argmax(scores))
        truth = int(np.argmax(labels))
        correct += int(pick == truth)
    return correct / float(len(decisions))


def greedy_baseline(decisions):
    """Baseline: pick the action with the most demand-move fraction, then fewer idles."""
    if not decisions:
        return 0.0
    demand_i = FEATURE_NAMES.index("demand_move_frac")
    idle_i = FEATURE_NAMES.index("action_is_idle")
    correct = 0
    for features_rows, labels in decisions:
        pick = max(
            range(len(features_rows)),
            key=lambda i: (features_rows[i][demand_i], -features_rows[i][idle_i]),
        )
        truth = int(np.argmax(labels))
        correct += int(pick == truth)
    return correct / float(len(decisions))


def main():
    train_x, train_y = [], []
    hold_x, hold_y = [], []
    train_decisions, hold_decisions = [], []
    solved = 0
    skipped = 0

    for _family, _index, payload, held_out in training_scenarios():
        scenario = load_scenario(payload, require_format_version=True)
        solution = run_dispatch(
            num_segments=8,
            num_trucks=scenario.fleet_size,
            scenario=scenario,
            time_limit_seconds=3,
        )
        if solution is None or run_dispatch.last_stop_reason != "optimal":
            skipped += 1
            continue
        solved += 1
        bucket_x = hold_x if held_out else train_x
        bucket_y = hold_y if held_out else train_y
        decisions = hold_decisions if held_out else train_decisions
        path = solution.path_from_root()
        for index in range(len(path) - 1):
            state = path[index].state
            chosen = path[index + 1].action
            options = list(state.possible_actions())
            if chosen not in options or len(options) < 2:
                continue
            rows, labels = [], []
            for action in options:
                row = action_features(state, action)
                label = 1.0 if action == chosen else 0.0
                rows.append(row)
                labels.append(label)
                bucket_x.append(row)
                bucket_y.append(label)
            decisions.append((rows, labels))

    if len(train_y) < 10:
        raise SystemExit("not enough training traces (%s)" % len(train_y))

    policy = train_policy(np.vstack(train_x), np.asarray(train_y), seed=0, steps=500)
    train_acc = decision_accuracy(policy, train_decisions)
    hold_acc = decision_accuracy(policy, hold_decisions)
    base_acc = greedy_baseline(hold_decisions)

    metadata = {
        "model_type": "dispatch-policy-mlp",
        "task": "imitate A* legal-action choice",
        "teacher": "core_search A*",
        "license": "mit",
        "trained_on": "synthetic format-v1 mine scenarios",
        "n_train_rows": len(train_y),
        "n_holdout_rows": len(hold_y),
        "n_train_decisions": len(train_decisions),
        "n_holdout_decisions": len(hold_decisions),
        "scenarios_solved": solved,
        "scenarios_skipped": skipped,
        "train_decision_accuracy": round(train_acc, 4),
        "holdout_decision_accuracy": round(hold_acc, 4),
        "holdout_greedy_baseline_accuracy": round(base_acc, 4),
        "note": "Scores legal dispatch actions. Does not prove optimality.",
    }
    DEFAULT_WEIGHTS.parent.mkdir(parents=True, exist_ok=True)
    policy.save(DEFAULT_WEIGHTS, DEFAULT_CONFIG, metadata)

    HUB_DIR.mkdir(parents=True, exist_ok=True)
    policy.save(HUB_DIR / "weights.npz", HUB_DIR / "config.json", metadata)
    print(json.dumps(metadata, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
