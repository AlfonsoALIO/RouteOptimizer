# Mine scenario file format

Version: **1** (`format_version` field)

This JSON format describes one mine for both the A\* dispatcher and the MILP
shift planner. It matches the Story 2.1 scenario schema, with an explicit
format version for on-disk files.

## Units

| Quantity | Unit |
|----------|------|
| Demand | tons |
| Truck capacity | tons |
| Shift length | hours |
| Arc travel time | minutes |

## Top-level fields

| Name | Type | Unit | Required | Description |
|------|------|------|----------|-------------|
| `format_version` | string | — | **yes** (files) | Format version. Supported: `"1"`. |
| `locations` | array of objects | — | yes | Named places with queue capacity. |
| `arcs` | array of objects | — | yes | Directed travel links. |
| `demands` | array of objects | — | yes | Haul demand by source/destination. |
| `trucks` | array of objects | — | yes | Fleet members and capacities. |
| `shift_length_hours` | number | hours | yes | Shift horizon length. |
| `fleet_size` | integer | trucks | yes | Maximum trucks available. |

## `locations[]`

| Name | Type | Unit | Required | Description |
|------|------|------|----------|-------------|
| `name` | string | — | yes | Unique location id (e.g. `garage`, `S1`). |
| `resident_capacity` | integer | trucks | yes | Max trucks that may queue here (≥ 0). |

## `arcs[]`

| Name | Type | Unit | Required | Description |
|------|------|------|----------|-------------|
| `source` | string | — | yes | Must name a location. |
| `destination` | string | — | yes | Must name a location. |
| `travel_time_minutes` | number | minutes | yes | Positive travel time. |
| `distance` | number | (optional) | no | Optional distance; unused by solvers today. |

## `demands[]`

| Name | Type | Unit | Required | Description |
|------|------|------|----------|-------------|
| `source` | string | — | yes | Must name a location. |
| `destination` | string | — | yes | Must name a location. |
| `tons` | number | tons | yes | Non-negative tonnage for the shift. |

## `trucks[]`

| Name | Type | Unit | Required | Description |
|------|------|------|----------|-------------|
| `name` | string | — | yes | Unique truck id. |
| `tonnage_capacity` | number | tons | yes | Positive payload capacity. |

## Validation

Loading a file through `core.scenario.load_scenario_file` rejects:

- a missing required field (error names the field)
- an unknown location on an arc or demand (error names the location)
- an unsupported `format_version` (error names the version)

## Sample files

| File | Status |
|------|--------|
| [`samples/tiny_feasible.json`](../samples/tiny_feasible.json) | Small feasible mine (dispatch + shift plan) |
| [`samples/toy_mine.json`](../samples/toy_mine.json) | Published synthetic fixture (dispatch) |
| Haul-history anonymized sample | **Not published** until the data owner approves release |

## Python API

```python
from core.scenario import load_scenario_file, write_scenario_file

scenario = load_scenario_file("samples/toy_mine.json")
write_scenario_file(scenario, "out/copy.json")
```
