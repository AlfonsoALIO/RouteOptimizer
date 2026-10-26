"""Story 6.5: Docker image for CLI solvers (no network at run time)."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TINY = ROOT / "samples" / "tiny_feasible.json"
IMAGE_NAME = os.environ.get("ROUTE_OPTIMIZER_IMAGE", "route-optimizer")


def _package_version():
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'(?m)^version\s*=\s*"([^"]+)"', text)
    assert match, "version missing from pyproject.toml"
    return match.group(1)


def _docker_available():
    if not shutil.which("docker"):
        return False
    probe = subprocess.run(
        ["docker", "info"],
        capture_output=True,
        text=True,
        check=False,
    )
    return probe.returncode == 0


requires_docker = pytest.mark.skipif(
    not _docker_available(),
    reason="Docker daemon not available",
)


def test_dockerfile_and_build_script_exist():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "PACKAGE_VERSION" in dockerfile
    assert "pip install" in dockerfile
    assert 'ENTRYPOINT ["route-optimizer"]' in dockerfile

    script = ROOT / "scripts" / "build_docker.sh"
    assert script.is_file()
    text = script.read_text(encoding="utf-8")
    assert "PACKAGE_VERSION" in text
    assert "pyproject.toml" in text


@requires_docker
def test_image_version_matches_package_and_commands_run_offline(tmp_path):
    version = _package_version()
    tag = "%s:%s" % (IMAGE_NAME, version)

    build = subprocess.run(
        ["bash", str(ROOT / "scripts" / "build_docker.sh")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "IMAGE_NAME": IMAGE_NAME},
    )
    assert build.returncode == 0, build.stderr + build.stdout
    assert tag in build.stdout

    inspect = subprocess.run(
        [
            "docker",
            "image",
            "inspect",
            tag,
            "--format",
            "{{ index .Config.Labels \"org.opencontainers.image.version\" }}",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert inspect.returncode == 0, inspect.stderr
    assert inspect.stdout.strip() == version

    work = tmp_path / "data"
    work.mkdir()
    scenario = work / "tiny_feasible.json"
    scenario.write_text(TINY.read_text(encoding="utf-8"), encoding="utf-8")

    dispatch_out = work / "dispatch.json"
    shift_out = work / "shift_plan.json"

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
    assert dispatch_out.is_file()
    dispatch_payload = json.loads(dispatch_out.read_text(encoding="utf-8"))
    assert dispatch_payload["status"] == "ok"
    assert dispatch_payload["optimal"] is True

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
    assert shift_out.is_file()
    shift_payload = json.loads(shift_out.read_text(encoding="utf-8"))
    assert shift_payload["proven_optimal"] is True
    assert shift_payload["status"] == "Optimal"
