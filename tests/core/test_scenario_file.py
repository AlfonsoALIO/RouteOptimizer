"""Story 6.2: documented scenario file format."""

import json
from pathlib import Path

import pytest

from core.fixtures import load_toy_mine, toy_mine_payload
from core.scenario import (
    SCENARIO_FORMAT_VERSION,
    ScenarioError,
    load_scenario,
    load_scenario_file,
    write_scenario_file,
)

ROOT = Path(__file__).resolve().parents[2]
SAMPLE = ROOT / "samples" / "toy_mine.json"


def test_sample_toy_mine_file_matches_fixture_loader():
    assert SAMPLE.is_file()
    from_file = load_scenario_file(SAMPLE)
    from_fixture = load_toy_mine()

    assert from_file.format_version == SCENARIO_FORMAT_VERSION
    assert from_file.locations == from_fixture.locations
    assert from_file.arcs == from_fixture.arcs
    assert from_file.demands == from_fixture.demands
    assert from_file.trucks == from_fixture.trucks
    assert from_file.shift_length_hours == from_fixture.shift_length_hours
    assert from_file.fleet_size == from_fixture.fleet_size


def test_round_trip_write_and_load(tmp_path):
    scenario = load_toy_mine()
    path = tmp_path / "mine.json"
    write_scenario_file(scenario, path)
    loaded = load_scenario_file(path)
    assert loaded.to_payload() == scenario.to_payload()


def test_missing_format_version_on_file_names_the_field(tmp_path):
    payload = toy_mine_payload()
    del payload["format_version"]
    path = tmp_path / "no_version.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ScenarioError, match="missing required field: format_version"):
        load_scenario_file(path)


def test_missing_required_field_names_the_field(tmp_path):
    payload = toy_mine_payload()
    del payload["demands"]
    path = tmp_path / "no_demands.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ScenarioError, match="missing required field: demands"):
        load_scenario_file(path)


def test_unknown_location_names_the_location(tmp_path):
    payload = toy_mine_payload()
    payload["arcs"].append(
        {
            "source": "S1",
            "destination": "NO_SUCH_PLACE",
            "travel_time_minutes": 10.0,
        }
    )
    path = tmp_path / "bad_arc.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ScenarioError, match="unknown location: NO_SUCH_PLACE"):
        load_scenario_file(path)


def test_unsupported_format_version_names_the_version(tmp_path):
    payload = toy_mine_payload()
    payload["format_version"] = "99"
    path = tmp_path / "v99.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ScenarioError, match="unsupported format version: 99"):
        load_scenario_file(path)


def test_in_memory_loader_defaults_missing_version_to_v1():
    payload = toy_mine_payload()
    del payload["format_version"]
    scenario = load_scenario(payload)
    assert scenario.format_version == SCENARIO_FORMAT_VERSION


def test_scenario_format_doc_lists_units_and_version():
    doc = (ROOT / "docs" / "scenario-format.md").read_text()
    assert "format_version" in doc
    assert "tons" in doc
    assert "hours" in doc
    assert "minutes" in doc
    assert "Required" in doc or "required" in doc
