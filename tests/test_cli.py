"""Story 6.3: pip-installable CLI for dispatch and shift-plan."""

import json
import socket
import subprocess
import sys
from pathlib import Path

import pytest

from route_optimizer import cli

ROOT = Path(__file__).resolve().parents[1]
TINY = ROOT / "samples" / "tiny_feasible.json"
TOY = ROOT / "samples" / "toy_mine.json"


def test_pyproject_declares_scripts_and_mit_without_commercial_solver():
    text = (ROOT / "pyproject.toml").read_text()
    assert "route-optimizer" in text
    assert "route-optimizer-dispatch" in text
    assert "route-optimizer-shift-plan" in text
    assert "PuLP" in text
    assert "LICENSE" in text
    assert "gurobi" not in text.lower()
    assert "cplex" not in text.lower()


def test_dispatch_writes_file_and_exits_zero(tmp_path):
    out = tmp_path / "dispatch.json"
    code = cli.main(
        [
            "dispatch",
            str(TINY),
            "-o",
            str(out),
            "--segments",
            "8",
            "--trucks",
            "2",
        ]
    )
    assert code == 0
    assert out.is_file()
    payload = json.loads(out.read_text())
    assert payload["status"] == "ok"
    assert payload["optimal"] is True
    assert payload["cost_minutes"] > 0


def test_shift_plan_writes_file_and_exits_zero(tmp_path):
    out = tmp_path / "plan.json"
    code = cli.main(
        ["shift-plan", str(TINY), "-o", str(out), "--segments", "4"]
    )
    assert code == 0
    payload = json.loads(out.read_text())
    assert payload["optimal"] is True
    assert payload["status"] == "Optimal"
    assert "inventory" in payload


def test_shift_plan_infeasible_exits_nonzero(tmp_path):
    bad = {
        "format_version": "1",
        "locations": [
            {"name": "garage", "resident_capacity": 1},
            {"name": "S", "resident_capacity": 1},
        ],
        "arcs": [
            {"source": "garage", "destination": "S", "travel_time_minutes": 15.0},
            {"source": "S", "destination": "garage", "travel_time_minutes": 15.0},
        ],
        "demands": [{"source": "S", "destination": "garage", "tons": 0.0}],
        "trucks": [
            {"name": "truck_%i" % i, "tonnage_capacity": 100.0} for i in range(1, 6)
        ],
        "shift_length_hours": 1.0,
        "fleet_size": 5,
    }
    scenario = tmp_path / "infeasible.json"
    scenario.write_text(json.dumps(bad), encoding="utf-8")
    out = tmp_path / "plan.json"
    code = cli.main(["shift-plan", str(scenario), "-o", str(out), "--segments", "2"])
    assert code != 0
    payload = json.loads(out.read_text())
    assert payload["optimal"] is False
    assert "Infeasible" in payload["status"]


def test_invalid_scenario_exits_nonzero_and_names_problem(tmp_path, capsys):
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"format_version": "1", "locations": []}), encoding="utf-8")
    out = tmp_path / "out.json"
    code = cli.main(["dispatch", str(bad), "-o", str(out)])
    assert code != 0
    err = capsys.readouterr().err
    assert "error:" in err
    assert "missing required field" in err or "locations" in err


def test_cli_modules_do_not_require_sql_or_network():
    # Import graph used by CLI must not pull SQL Server access
    import route_optimizer.cli as cli_mod

    source = Path(cli_mod.__file__).read_text()
    assert "data_access" not in source
    assert "pyodbc" not in source
    assert "fetch_from_sqlserver" not in source


def test_cli_runs_with_network_blocked(tmp_path, monkeypatch):
    def blocked(*_args, **_kwargs):
        raise OSError("network disabled for test")

    monkeypatch.setattr(socket, "create_connection", blocked)

    out = tmp_path / "plan.json"
    code = cli.main(
        ["shift-plan", str(TINY), "-o", str(out), "--segments", "4"]
    )
    assert code == 0
    assert out.is_file()


def test_clean_pip_install_to_prefix_exposes_scripts(tmp_path):
    """pip install into a clean prefix registers console scripts (no commercial solver)."""
    prefix = tmp_path / "prefix"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            str(ROOT),
            "--no-deps",
            "--prefix",
            str(prefix),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr + result.stdout

    # Entry-point wrappers land under bin/ (Unix) or Scripts/ (Windows)
    bin_dirs = [prefix / "bin", prefix / "Scripts"]
    found = []
    for bin_dir in bin_dirs:
        if bin_dir.is_dir():
            found.extend(p.name for p in bin_dir.iterdir())
    assert "route-optimizer" in found or "route-optimizer.exe" in found
    assert any(name.startswith("route-optimizer-dispatch") for name in found)
    assert any(name.startswith("route-optimizer-shift-plan") for name in found)
