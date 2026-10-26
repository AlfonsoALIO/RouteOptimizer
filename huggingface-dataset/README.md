---
license: mit
pretty_name: RouteOptimizer synthetic mine scenarios
language:
  - en
tags:
  - mining
  - optimization
  - synthetic
  - operations-research
  - fleet-dispatch
size_categories:
  - n<1K
configs:
  - config_name: default
    data_files:
      - split: train
        path: data/scenarios.jsonl
---

# RouteOptimizer synthetic mine scenarios

Synthetic **mine scenario files** for [RouteOptimizer](https://huggingface.co/albones80/route-optimizer), an operations-research solver (A\* dispatch and MILP shift plans). **Not a machine-learning dataset and not real haul history.** There are no trained weights.

Each row is one format-version-1 scenario plus a short solver probe so you can filter easy vs. hard cases.

Rights: Alfonso Bonillas / [alioit.com](https://www.alioit.com/route-optimizer). License: **MIT**.

## What is in the box

| Piece | Contents |
|-------|----------|
| [`data/scenarios.jsonl`](data/scenarios.jsonl) | One row per scenario (table columns + `scenario_json`) |
| [`scenarios/`](scenarios/) | The same scenarios as standalone JSON files |
| `tiny_feasible`, `toy_mine` | The published samples from the solver repo |
| `shuttle-*`, `two_shovel-*`, `ore_waste-*` | Generated synthetic mines |

Families:

- **shuttle** — garage, one shovel, one crusher
- **two_shovel** — two shovels feeding one crusher
- **ore_waste** — one shovel, ore to a crusher and waste to a dump
- **canonical** — `tiny_feasible` and `toy_mine` copied from the solver repository

A haul-history sample is **not** included. It will be published only after the data owner approves release.

## Solver labels

Labels are probes, not a promise about every horizon:

| Column | Meaning |
|--------|---------|
| `shift_plan_status` | PuLP/CBC status on a **4-segment** horizon (`time_limit` 8s) |
| `shift_plan_proven_optimal` | CBC proved optimality on that probe |
| `dispatch_status` | A\* result on **8 segments** with a 5s cap, or `not_evaluated` when the fleet or tonnage is larger |
| `dispatch_optimal` | A\* finished and reported an optimal dispatch on that probe |
| `total_tons` | Sum of demand tons |
| `scenario_json` | Full scenario file (format version `"1"`) |

Units: tons, hours, minutes. Field definitions: [scenario format](https://huggingface.co/albones80/route-optimizer/blob/main/docs/scenario-format.md).

## Load it

```python
from datasets import load_dataset
import json

ds = load_dataset("albones80/route-optimizer-scenarios", split="train")
scenario = json.loads(ds[0]["scenario_json"])
```

Or download one file and run the solver:

```bash
route-optimizer dispatch scenarios/shuttle-001.json -o out/dispatch.json --segments 8 --trucks 2
route-optimizer shift-plan scenarios/shuttle-001.json -o out/shift_plan.json --segments 4
```

Install the solver from [albones80/route-optimizer](https://huggingface.co/albones80/route-optimizer) or [GitHub](https://github.com/AlfonsoALIO/RouteOptimizer).

## Regenerate

From the RouteOptimizer repo (same seeds every time):

```bash
python scripts/generate_synthetic_scenarios.py
```

## Links

| Resource | URL |
|----------|-----|
| Solver (Hub) | https://huggingface.co/albones80/route-optimizer |
| Source | https://github.com/AlfonsoALIO/RouteOptimizer |
| License | MIT |
