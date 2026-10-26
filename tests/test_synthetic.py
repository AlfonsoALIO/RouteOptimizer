"""Synthetic mine scenarios for the Hugging Face dataset."""

import json
from pathlib import Path

from core.scenario import load_scenario
from core.synthetic import synthetic_catalog

ROOT = Path(__file__).resolve().parents[1]
JSONL = ROOT / "huggingface-dataset" / "data" / "scenarios.jsonl"
SCENARIOS = ROOT / "huggingface-dataset" / "scenarios"


def test_catalog_is_valid_and_deterministic():
    first = synthetic_catalog()
    second = synthetic_catalog()
    assert len(first) == 20
    assert [row["id"] for row in first] == [row["id"] for row in second]
    families = {row["family"] for row in first}
    assert families == {"shuttle", "two_shovel", "ore_waste"}
    for row in first:
        scenario = load_scenario(row["scenario"], require_format_version=True)
        assert scenario.fleet_size == len(scenario.trucks)
        assert scenario.fleet_size > 0
        names = {loc["name"] for loc in scenario.locations}
        assert "garage" in names
        assert all(d["tons"] >= 0 for d in scenario.demands)


def test_dataset_snapshot_matches_catalog():
    assert JSONL.is_file()
    rows = [
        json.loads(line)
        for line in JSONL.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    ids = [row["id"] for row in rows]
    assert ids[:2] == ["tiny_feasible", "toy_mine"]
    generated = {row["id"] for row in synthetic_catalog()}
    assert generated <= set(ids)
    assert len(rows) == 2 + len(generated)

    card = (ROOT / "huggingface-dataset" / "README.md").read_text(encoding="utf-8")
    assert "license: mit" in card.lower()
    assert "synthetic" in card.lower()
    assert "not real haul history" in card.lower() or "Not a machine-learning" in card

    sample = json.loads(rows[2]["scenario_json"])
    load_scenario(sample, require_format_version=True)
    path = SCENARIOS / ("%s.json" % rows[2]["id"])
    assert path.is_file()
    assert json.loads(path.read_text(encoding="utf-8"))["format_version"] == "1"
