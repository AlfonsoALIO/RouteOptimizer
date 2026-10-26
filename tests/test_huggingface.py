"""Story 6.6: Hugging Face repository content and sample runs."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from route_optimizer import cli

ROOT = Path(__file__).resolve().parents[1]
HF = ROOT / "huggingface"
SAMPLES = ROOT / "samples"
TINY = SAMPLES / "tiny_feasible.json"
TOY = SAMPLES / "toy_mine.json"


def test_hub_readme_states_scope_license_and_no_weights():
    text = (HF / "README.md").read_text(encoding="utf-8")
    lower = text.lower()
    assert "license: mit" in lower
    assert "mit" in lower
    assert "dispatch_policy" in lower
    assert "weights.npz" in lower
    assert "does not prove" in lower or "not prove" in lower
    assert "optimization" in lower
    assert "what it does" in lower
    assert "what it does not do" in lower
    assert "pip" in lower
    assert "docker" in lower
    assert "scenario-format" in lower
    assert "tiny_feasible.json" in text
    assert "toy_mine.json" in text
    assert "github.com/AlfonsoALIO/RouteOptimizer" in text
    assert "route-optimizer" in lower


def test_hub_includes_samples_and_format_matching_repo():
    assert (HF / "LICENSE").is_file()
    assert (HF / "docs" / "scenario-format.md").is_file()
    for name in ("tiny_feasible.json", "toy_mine.json"):
        hub = HF / "samples" / name
        src = SAMPLES / name
        assert hub.is_file()
        assert hub.read_text(encoding="utf-8") == src.read_text(encoding="utf-8")


def test_hub_readme_embeds_demo_visuals():
    text = (HF / "README.md").read_text(encoding="utf-8")
    assert "assets/demo-cli.gif" in text
    assert "assets/demo-cli.png" in text
    assert (HF / "assets" / "demo-cli.gif").is_file()
    assert (HF / "assets" / "demo-cli.png").is_file()
    assert (HF / "assets" / "hub-hero.png").is_file()


def test_sample_via_pip_cli_returns_dispatch_and_shift_plan(tmp_path):
    """Install-method stand-in: in-process CLI (same entry as pip console scripts)."""
    dispatch_out = tmp_path / "dispatch.json"
    shift_out = tmp_path / "shift.json"

    code = cli.main(
        [
            "dispatch",
            str(TINY),
            "-o",
            str(dispatch_out),
            "--segments",
            "8",
            "--trucks",
            "2",
        ]
    )
    assert code == 0
    dispatch = json.loads(dispatch_out.read_text(encoding="utf-8"))
    assert dispatch["status"] == "ok"
    assert dispatch["optimal"] is True

    code = cli.main(
        ["shift-plan", str(TINY), "-o", str(shift_out), "--segments", "4"]
    )
    assert code == 0
    shift = json.loads(shift_out.read_text(encoding="utf-8"))
    assert shift["proven_optimal"] is True
    assert "inventory" in shift

    # Larger sample: dispatch completes (Hub ships both Story 6.2 files)
    toy_out = tmp_path / "toy_dispatch.json"
    code = cli.main(
        [
            "dispatch",
            str(TOY),
            "-o",
            str(toy_out),
            "--segments",
            "58",
            "--trucks",
            "21",
        ]
    )
    assert code == 0
    assert json.loads(toy_out.read_text(encoding="utf-8"))["status"] == "ok"


def _docker_available():
    if not shutil.which("docker"):
        return False
    return (
        subprocess.run(
            ["docker", "info"], capture_output=True, text=True, check=False
        ).returncode
        == 0
    )


@pytest.mark.skipif(not _docker_available(), reason="Docker daemon not available")
def test_sample_via_docker_returns_dispatch_and_shift_plan(tmp_path):
    version = "0.1.0"
    tag = "route-optimizer:%s" % version
    inspect = subprocess.run(
        ["docker", "image", "inspect", tag],
        capture_output=True,
        text=True,
        check=False,
    )
    if inspect.returncode != 0:
        build = subprocess.run(
            ["bash", str(ROOT / "scripts" / "build_docker.sh")],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        assert build.returncode == 0, build.stderr + build.stdout

    work = tmp_path / "data"
    work.mkdir()
    (work / "tiny_feasible.json").write_text(
        TINY.read_text(encoding="utf-8"), encoding="utf-8"
    )
    (work / "toy_mine.json").write_text(
        TOY.read_text(encoding="utf-8"), encoding="utf-8"
    )

    dispatch = subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "--network=none",
            "-v",
            "%s:/data" % work,
            tag,
            "dispatch",
            "/data/tiny_feasible.json",
            "-o",
            "/data/dispatch.json",
            "--segments",
            "8",
            "--trucks",
            "2",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert dispatch.returncode == 0, dispatch.stderr + dispatch.stdout
    assert json.loads((work / "dispatch.json").read_text())["status"] == "ok"

    shift = subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "--network=none",
            "-v",
            "%s:/data" % work,
            tag,
            "shift-plan",
            "/data/tiny_feasible.json",
            "-o",
            "/data/shift_plan.json",
            "--segments",
            "4",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert shift.returncode == 0, shift.stderr + shift.stdout
    assert json.loads((work / "shift_plan.json").read_text())["proven_optimal"] is True

    toy = subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "--network=none",
            "-v",
            "%s:/data" % work,
            tag,
            "dispatch",
            "/data/toy_mine.json",
            "-o",
            "/data/toy_dispatch.json",
            "--segments",
            "58",
            "--trucks",
            "21",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert toy.returncode == 0, toy.stderr + toy.stdout
    assert json.loads((work / "toy_dispatch.json").read_text())["status"] == "ok"


def test_publish_and_sync_scripts_exist():
    assert (ROOT / "scripts" / "sync_huggingface.sh").is_file()
    assert (ROOT / "scripts" / "publish_huggingface.sh").is_file()
    # Do not require HF_TOKEN in CI; script must refuse without it
    result = subprocess.run(
        ["bash", str(ROOT / "scripts" / "publish_huggingface.sh")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
        env={k: v for k, v in os.environ.items() if k not in ("HF_TOKEN", "HUGGING_FACE_HUB_TOKEN")},
    )
    assert result.returncode != 0
    assert "HF_TOKEN" in (result.stderr + result.stdout)
