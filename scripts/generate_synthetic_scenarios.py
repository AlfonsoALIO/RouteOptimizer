#!/usr/bin/env python3
"""Write the Hugging Face dataset snapshot under huggingface-dataset/.

Generates synthetic format-v1 scenarios, copies the published samples, and
labels each row with a short MILP solve (and a short A* run when the fleet
is small).
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.scenario import load_scenario, write_scenario_file  # noqa: E402
from core.synthetic import catalog_features, synthetic_catalog  # noqa: E402
from core.batch import run_batch  # noqa: E402
from core_search.run import run as run_dispatch  # noqa: E402

DEST = ROOT / "huggingface-dataset"
SCENARIO_DIR = DEST / "scenarios"
DATA_DIR = DEST / "data"
CANONICAL = (
    ("tiny_feasible", ROOT / "samples" / "tiny_feasible.json", "published_sample"),
    ("toy_mine", ROOT / "samples" / "toy_mine.json", "published_sample"),
)


def _label(scenario):
    """Attach solver outcomes. Dispatch is skipped on larger fleets."""
    shift = run_batch(
        scenario,
        persist=False,
        num_segments=4,
        time_limit_seconds=8,
    )
    labels = {
        "shift_plan_segments": 4,
        "shift_plan_status": shift.status_name,
        "shift_plan_proven_optimal": bool(shift.proven_optimal),
        "dispatch_segments": -1,
        "dispatch_status": "not_evaluated",
        "dispatch_optimal": False,
        "dispatch_cost_minutes": -1.0,
    }
    fleet = int(scenario.fleet_size)
    total_tons = sum(float(d["tons"]) for d in scenario.demands)
    if fleet <= 4 and total_tons <= 800 and scenario.shift_length_hours <= 4:
        solution = run_dispatch(
            num_segments=8,
            num_trucks=fleet,
            scenario=scenario,
            time_limit_seconds=5,
        )
        reason = run_dispatch.last_stop_reason
        labels["dispatch_segments"] = 8
        labels["dispatch_status"] = "ok" if solution is not None else (reason or "no_solution")
        labels["dispatch_optimal"] = reason == "optimal" and solution is not None
        if solution is not None:
            labels["dispatch_cost_minutes"] = float(solution.cost)
    return labels


def _row_from_payload(row_id, family, seed, source, payload):
    scenario = load_scenario(payload, require_format_version=True)
    features = catalog_features(
        {
            "id": row_id,
            "family": family,
            "seed": seed,
            "source": source,
            "scenario": scenario.to_payload(),
        }
    )
    labels = _label(scenario)
    record = dict(features)
    record.update(labels)
    record["scenario_json"] = json.dumps(scenario.to_payload(), sort_keys=True)
    return record, scenario


def main():
    SCENARIO_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    records = []

    for name, path, source in CANONICAL:
        payload = json.loads(path.read_text(encoding="utf-8"))
        record, scenario = _row_from_payload(name, "canonical", 0, source, payload)
        write_scenario_file(scenario, SCENARIO_DIR / ("%s.json" % name))
        records.append(record)
        print(
            "%s  shift=%s  dispatch=%s"
            % (name, record["shift_plan_status"], record["dispatch_status"])
        )

    for row in synthetic_catalog():
        record, scenario = _row_from_payload(
            row["id"],
            row["family"],
            row["seed"],
            row["source"],
            row["scenario"],
        )
        write_scenario_file(scenario, SCENARIO_DIR / ("%s.json" % row["id"]))
        records.append(record)
        print(
            "%s  shift=%s  dispatch=%s  tons=%s"
            % (
                row["id"],
                record["shift_plan_status"],
                record["dispatch_status"],
                record["total_tons"],
            )
        )

    jsonl_path = DATA_DIR / "scenarios.jsonl"
    with jsonl_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, sort_keys=True))
            handle.write("\n")

    # Keep a copy of the license next to the dataset card.
    shutil.copyfile(ROOT / "LICENSE", DEST / "LICENSE")
    print("wrote %s (%i rows)" % (jsonl_path, len(records)))


if __name__ == "__main__":
    main()
