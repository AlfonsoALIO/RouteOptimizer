"""Gradio demo: run RouteOptimizer dispatch or shift-plan on bundled samples."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import gradio as gr

from route_optimizer.cli import cmd_dispatch, cmd_shift_plan
from route_optimizer import policy as policy_mod

ROOT = Path(__file__).resolve().parent
SAMPLES = {
    "tiny_feasible (fast)": ROOT / "samples" / "tiny_feasible.json",
    "toy_mine (larger)": ROOT / "samples" / "toy_mine.json",
}


class _Args:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


def _policy_blurb():
    config_file = Path(policy_mod.DEFAULT_WEIGHTS).with_name("dispatch_policy_config.json")
    if not config_file.is_file():
        return "Learned dispatch policy checkpoint is packaged with `route-optimizer`."
    cfg = json.loads(config_file.read_text(encoding="utf-8"))
    bits = ["**ML dispatch policy** loaded from the packaged Hugging Face checkpoint."]
    acc = cfg.get("holdout_decision_accuracy")
    base = cfg.get("holdout_greedy_baseline_accuracy")
    if acc is not None:
        bits.append("Holdout decision accuracy vs A* teacher: **%.1f%%**." % (100.0 * float(acc)))
    if base is not None:
        bits.append("Demand-greedy baseline: **%.1f%%**." % (100.0 * float(base)))
    bits.append("The policy ranks legal moves; A* / CBC still produce proven plans.")
    return " ".join(bits)


def run_solver(sample_name, mode, segments, trucks, time_limit):
    sample_path = SAMPLES[sample_name]
    if not sample_path.is_file():
        return "Sample not found: %s" % sample_path, ""

    seg = int(segments) if segments not in (None, "") else None
    trk = int(trucks) if trucks not in (None, "") else None
    limit = float(time_limit) if time_limit not in (None, "") and float(time_limit) > 0 else None

    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "result.json"
        if mode == "dispatch":
            args = _Args(
                scenario=str(sample_path),
                output=str(out),
                segments=seg,
                trucks=trk,
                time_limit=limit,
            )
            code = cmd_dispatch(args)
        else:
            args = _Args(
                scenario=str(sample_path),
                output=str(out),
                segments=seg if seg is not None else 4,
                time_limit=limit,
            )
            code = cmd_shift_plan(args)

        text = out.read_text(encoding="utf-8") if out.is_file() else "{}"
        payload = json.loads(text)
        summary = {
            "exit_code": code,
            "mode": mode,
            "sample": sample_name,
            "status": payload.get("status"),
            "optimal": payload.get("optimal"),
            "proven_optimal": payload.get("proven_optimal"),
            "time_limit_reached": payload.get("time_limit_reached"),
            "cost_minutes": payload.get("cost_minutes"),
            "stop_reason": payload.get("stop_reason"),
            "num_segments": payload.get("num_segments"),
            "num_trucks": payload.get("num_trucks"),
        }
        return json.dumps(summary, indent=2), text


def build_ui():
    with gr.Blocks(title="RouteOptimizer") as demo:
        gr.Markdown(
            """
# RouteOptimizer
Open-source **machine-learning + OR** stack for mine fleet dispatch from [Alio IT](https://www.alioit.com/route-optimizer).

Pick a sample scenario, run **A\\* dispatch** or a **CBC shift plan**, and inspect the JSON.
"""
        )
        gr.Markdown(_policy_blurb())
        with gr.Row():
            sample = gr.Dropdown(
                choices=list(SAMPLES.keys()),
                value=list(SAMPLES.keys())[0],
                label="Sample scenario",
            )
            mode = gr.Radio(
                choices=["dispatch", "shift-plan"],
                value="dispatch",
                label="Solver",
            )
        with gr.Row():
            segments = gr.Number(value=8, label="Segments", precision=0)
            trucks = gr.Number(value=2, label="Trucks (dispatch)", precision=0)
            time_limit = gr.Number(value=30, label="Time limit (seconds)", precision=0)
        run = gr.Button("Run", variant="primary")
        summary = gr.Code(label="Summary", language="json")
        detail = gr.Code(label="Full JSON", language="json")
        run.click(
            run_solver,
            inputs=[sample, mode, segments, trucks, time_limit],
            outputs=[summary, detail],
        )
        gr.Markdown(
            """
[GitHub](https://github.com/AlfonsoALIO/RouteOptimizer) ·
[Model](https://huggingface.co/albones80/route-optimizer) ·
[Scenarios](https://huggingface.co/datasets/albones80/route-optimizer-scenarios) ·
[alioit.com](https://www.alioit.com/route-optimizer) · MIT
"""
        )
    return demo


demo = build_ui()

if __name__ == "__main__":
    demo.launch()
