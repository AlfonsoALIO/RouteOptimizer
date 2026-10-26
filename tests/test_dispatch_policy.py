"""Learned dispatch policy checkpoint."""

import json
from pathlib import Path

from core.scenario import load_scenario_file
from core_search.scenario_bridge import fleet_state_from_scenario
from route_optimizer.policy import FEATURE_NAMES, action_features, load_policy

ROOT = Path(__file__).resolve().parents[1]
TINY = ROOT / "samples" / "tiny_feasible.json"


def test_checkpoint_loads_and_picks_a_legal_action():
    config = json.loads(
        (ROOT / "route_optimizer" / "dispatch_policy_config.json").read_text(encoding="utf-8")
    )
    assert config["model_type"] == "dispatch-policy-mlp"
    assert config["holdout_decision_accuracy"] > config["holdout_greedy_baseline_accuracy"]
    assert config["holdout_decision_accuracy"] >= 0.8

    policy = load_policy()
    scenario = load_scenario_file(TINY)
    state = fleet_state_from_scenario(scenario, num_segments=8, num_trucks=2)
    action = policy.choose(state)
    assert action is not None
    assert action in state.possible_actions()
    row = action_features(state, action)
    assert row.shape == (len(FEATURE_NAMES),)
    assert 0.0 <= policy.score(state, action) <= 1.0
