---
title: RouteOptimizer Demo
emoji: 🛻
colorFrom: yellow
colorTo: gray
sdk: gradio
sdk_version: 4.44.1
app_file: app.py
pinned: false
license: mit
tags:
  - mining
  - optimization
  - operations-research
  - fleet-dispatch
short_description: Run A* mine dispatch or a CBC shift plan from a sample scenario
---

# RouteOptimizer Demo

Interactive demo for [RouteOptimizer](https://github.com/AlfonsoALIO/RouteOptimizer):
open-source mine fleet dispatch.

- **Dispatch (A\*)** — truck movement plan over a shift
- **Shift plan (MILP)** — mine-wide flow with PuLP + CBC
- **Learned policy** — small network on Hugging Face that imitates A\* among legal moves

Model: [albones80/route-optimizer](https://huggingface.co/albones80/route-optimizer)  
Company: [alioit.com/route-optimizer](https://www.alioit.com/route-optimizer)  
License: MIT
