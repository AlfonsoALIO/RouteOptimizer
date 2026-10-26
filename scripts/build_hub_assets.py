#!/usr/bin/env python3
"""Rebuild huggingface/assets demo GIF and PNGs from a live CLI run."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "huggingface" / "assets"
DEMO = ROOT / "out" / "demo"
TINY = ROOT / "samples" / "tiny_feasible.json"

BG = (18, 22, 28)
PANEL = (28, 34, 42)
BORDER = (55, 65, 78)
MUTED = (140, 155, 170)
TEXT = (230, 236, 242)
GREEN = (86, 196, 140)
COPPER = (210, 140, 70)
CYAN = (110, 190, 210)
AMBER = (230, 180, 90)
W, H = 1280, 720


def font(size, mono=False):
    candidates = (
        [
            "/System/Library/Fonts/Menlo.ttc",
            "/System/Library/Fonts/Monaco.ttf",
        ]
        if mono
        else [
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
            "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
        ]
    )
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


F_TITLE = font(36)
F_SUB = font(20)
F_TERM = font(22, mono=True)
F_SMALL = font(16, mono=True)
F_BADGE = font(18)


def rounded_rect(draw, xy, radius, fill, outline=None, width=1):
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def draw_window_chrome(draw, x, y, w, h, title):
    rounded_rect(draw, (x, y, x + w, y + h), 14, PANEL, BORDER, 2)
    for i, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        draw.ellipse((x + 16 + i * 22, y + 14, x + 28 + i * 22, y + 26), fill=c)
    draw.text((x + w // 2, y + 12), title, font=F_SMALL, fill=MUTED, anchor="mt")
    return y + 42


def base_canvas(subtitle):
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    draw.text((48, 28), "RouteOptimizer", font=F_TITLE, fill=TEXT)
    draw.text((48, 74), subtitle, font=F_SUB, fill=MUTED)
    badge = "MIT · offline · learned dispatch policy"
    bw = draw.textlength(badge, font=F_BADGE) + 24
    rounded_rect(draw, (W - 48 - bw, 32, W - 48, 64), 8, (36, 44, 54), COPPER, 1)
    draw.text((W - 48 - bw / 2, 48), badge, font=F_BADGE, fill=COPPER, anchor="mm")
    return img, draw


def frame_command():
    img, draw = base_canvas("Mine fleet dispatch (A*) + shift plan (MILP/CBC)")
    y = draw_window_chrome(draw, 48, 120, W - 96, 520, "terminal — route-optimizer")
    lines = [
        (MUTED, "$ route-optimizer dispatch samples/tiny_feasible.json \\"),
        (MUTED, "    -o out/dispatch.json --segments 8 --trucks 2"),
        (TEXT, ""),
        (GREEN, "dispatch: wrote out/dispatch.json (cost_minutes=75.0)"),
        (TEXT, ""),
        (MUTED, "$ route-optimizer shift-plan samples/tiny_feasible.json \\"),
        (MUTED, "    -o out/shift_plan.json --segments 4"),
        (TEXT, ""),
        (GREEN, "shift-plan: wrote out/shift_plan.json (status=Optimal)"),
    ]
    yy = y + 24
    for color, line in lines:
        draw.text((72, yy), line, font=F_TERM, fill=color)
        yy += 36
    return img


def frame_json_focus(dispatch, which="dispatch"):
    img, draw = base_canvas("Scenario JSON in → plan JSON out (no SQL, no network)")
    y = draw_window_chrome(draw, 48, 120, 560, 520, "cli")
    cmd_lines = [
        "$ route-optimizer dispatch \\",
        "  tiny_feasible.json \\",
        "  -o dispatch.json",
        "",
        "✓ status: ok",
        "✓ optimal: true",
        "✓ cost_minutes: %s" % dispatch["cost_minutes"],
    ]
    yy = y + 28
    for line in cmd_lines:
        color = GREEN if line.startswith("✓") else (CYAN if line.startswith("$") else TEXT)
        draw.text((72, yy), line, font=F_TERM, fill=color)
        yy += 40

    title = "out/dispatch.json" if which == "dispatch" else "out/shift_plan.json"
    y = draw_window_chrome(draw, 640, 120, 592, 520, title)
    if which == "dispatch":
        snippet = {
            "status": "ok",
            "optimal": True,
            "cost_minutes": dispatch["cost_minutes"],
            "num_trucks": 2,
            "steps": [
                {"truck": "truck_1", "source": "garage", "destination": "S"},
                {"truck": "truck_2", "source": "garage", "destination": "S"},
            ],
        }
    else:
        snippet = {
            "status": "Optimal",
            "proven_optimal": True,
            "fleet_size": 2,
            "flow": {"S->C": [1, 1, 1, 1]},
            "inventory": {"S": [2, 1, 1, 1, 0]},
        }
    yy = y + 20
    for line in json.dumps(snippet, indent=2).splitlines():
        color = AMBER if ":" in line and not line.strip().startswith(("{", "}", "[", "]")) else TEXT
        if any(k in line for k in ("true", "Optimal", "ok")):
            color = GREEN
        draw.text((664, yy), line[:52], font=F_SMALL, fill=color)
        yy += 26
        if yy > 600:
            break
    return img


def frame_pipeline():
    img, draw = base_canvas("From mine scenario to dispatch + shift plan")
    boxes = [
        (80, 220, 340, 420, "1. Scenario", "tiny_feasible.json\nlocations · arcs\ndemands · trucks"),
        (470, 220, 730, 420, "2. Solvers", "A* dispatch\nMILP + CBC\n--time-limit OK"),
        (860, 220, 1200, 420, "3. Results", "dispatch.json\nshift_plan.json\nproven_optimal"),
    ]
    for x0, y0, x1, y1, title, body in boxes:
        rounded_rect(
            draw,
            (x0, y0, x1, y1),
            16,
            PANEL,
            COPPER if "Solvers" in title else BORDER,
            2,
        )
        draw.text(((x0 + x1) / 2, y0 + 36), title, font=F_SUB, fill=COPPER, anchor="mt")
        by = y0 + 90
        for line in body.split("\n"):
            draw.text(((x0 + x1) / 2, by), line, font=F_TERM, fill=TEXT, anchor="mt")
            by += 40
    for x in (360, 750):
        draw.polygon([(x, 310), (x + 40, 330), (x, 350)], fill=CYAN)
    draw.text((W / 2, 500), "pip install · Docker · offline", font=F_SUB, fill=MUTED, anchor="mt")
    return img


def run_cli():
    DEMO.mkdir(parents=True, exist_ok=True)
    py = ROOT / ".venv" / "bin" / "python"
    exe = [str(py) if py.exists() else sys.executable, "-m", "route_optimizer.cli"]
    subprocess.run(
        exe
        + [
            "dispatch",
            str(TINY),
            "-o",
            str(DEMO / "dispatch.json"),
            "--segments",
            "8",
            "--trucks",
            "2",
        ],
        cwd=str(ROOT),
        check=True,
    )
    subprocess.run(
        exe
        + [
            "shift-plan",
            str(TINY),
            "-o",
            str(DEMO / "shift_plan.json"),
            "--segments",
            "4",
        ],
        cwd=str(ROOT),
        check=True,
    )


def main():
    run_cli()
    dispatch = json.loads((DEMO / "dispatch.json").read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)

    hero = frame_pipeline()
    hero.save(OUT / "hub-hero.png", "PNG", optimize=True)

    still = frame_json_focus(dispatch, "dispatch")
    still.save(OUT / "demo-cli.png", "PNG", optimize=True)

    frames = [
        frame_pipeline(),
        frame_command(),
        frame_json_focus(dispatch, "dispatch"),
        frame_json_focus(dispatch, "shift"),
        frame_command(),
    ]
    frames[0].save(
        OUT / "demo-cli.gif",
        save_all=True,
        append_images=frames[1:],
        duration=[2200, 2800, 3200, 3200, 2400],
        loop=0,
        optimize=False,
    )
    print("wrote", OUT / "hub-hero.png")
    print("wrote", OUT / "demo-cli.png")
    print("wrote", OUT / "demo-cli.gif")


if __name__ == "__main__":
    main()
