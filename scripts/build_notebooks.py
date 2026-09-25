#!/usr/bin/env python
"""Regenerate the ten narrative notebooks under ``notebooks/``.

The notebooks are thin wrappers: they import the same ``src`` modules the
test suite exercises, so the science lives in one place. This script keeps
their structure consistent and reviewable in plain text.

Usage:
    python scripts/build_notebooks.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOKS = ROOT / "notebooks"

HEADER = """\
%matplotlib inline
import sys

sys.path.insert(0, "..")

import matplotlib.pyplot as plt

import src.experiments as EX
import src.plotting as PL

cfg = EX.load_config("../config/defaults.yaml")
TRIALS = 5000
print("config loaded; primary q =", cfg["attacker_shares"]["primary"])
"""


def md(source: str) -> dict:
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": source.strip().splitlines(keepends=True),
    }


def code(source: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": source.strip().splitlines(keepends=True),
    }


def notebook(title: str, body: str) -> dict:
    return {
        "cells": [
            md(title),
            code(HEADER),
            md(body.split("```python")[0].strip()),
            code(body.split("```python", 1)[1].split("```", 1)[0]),
        ],
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python", "version": "3.10"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


SPECS: dict[str, dict] = {
    "01_analytical_baseline": {
        "title": "# 01 — Analytical baseline (plan section 9)\n"
        "Exact negative-binomial reversal probabilities versus the Poisson "
        "approximation, across attacker shares and confirmation depths.",
        "body": """
The exact model conditions on the attacker's block count at acceptance;
the Poisson approximation assumes a fixed acceptance time. They agree to
within sampling error at small q and separate at large q.

```python
res = EX.p0_analytical_baseline(cfg)
frame = res.frame()
frame.groupby(["attacker_share", "tie_policy"])["success_probability"].first().unstack()

fig = PL.fig2_reversal_vs_depth(cfg, results={"P0": res})
plt.show()
```
""",
    },
    "02_validate_simulators": {
        "title": "# 02 — Simulator validation (plan section 10)\n"
        "Event-driven and distribution-based Monte Carlo against the closed "
        "form. Every analytical value must fall inside the Wilson interval.",
        "body": """
```python
res = EX.p1_validate_simulators(cfg, trials=TRIALS)
cells = res.data["cells"]
print("cells within 95% CI:", sum(c["within_ci"] for c in cells), "/", len(cells))

fig = PL.fig1_analytical_vs_mc(cfg, results={"P1": res})
plt.show()
```
""",
    },
    "03_core_claim": {
        "title": "# 03 — Core claim: 2×60s vs 1×600s (sections 11, 39)\n"
        "The proponent's central claim under the persistent-minority model.",
        "body": """
```python
res = EX.p2_policy_comparison(cfg, trials=TRIALS)
res.frame()[["acceptance_policy", "success_probability", "ci_lower", "ci_upper"]]

fig = PL.fig3_focused_policies(cfg, results={"P2": res})
plt.show()
```
""",
    },
    "04_chainwork_vs_confirmations": {
        "title": "# 04 — Equal chainwork (plan section 15)\n"
        "Match policies by expected chainwork instead of confirmation count.",
        "body": """
```python
res = EX.p6_equal_chainwork(cfg, trials=TRIALS)
res.frame()[["acceptance_policy", "expected_work", "success_probability"]]

fig = PL.fig6_equal_chainwork(cfg, results={"P6": res})
plt.show()
```
""",
    },
    "05_equal_time": {
        "title": "# 05 — Equal elapsed time (plan section 16)\n"
        "Condition on wall-clock time since inclusion rather than confirmations.",
        "body": """
```python
res = EX.p7_equal_elapsed_time(cfg, trials=TRIALS)
res.frame()[["attack_deadline_sec", "target_interval_sec", "success_probability"]]

fig = PL.fig7_reversal_vs_time(cfg, results={"P7": res})
plt.show()
```
""",
    },
    "06_security_latency": {
        "title": "# 06 — Security/latency frontier (plan section 17)\n"
        "Trade reversible risk against confirmation latency per attacker share.",
        "body": """
```python
res = EX.p8_frontier(cfg, trials=TRIALS)
res.frame()[["attacker_share", "acceptance_policy", "median_wait_sec",
             "success_probability"]]

fig = PL.fig8_frontier(cfg, results={"P8": res})
plt.show()
```
""",
    },
    "07_36x_claim": {
        "title": "# 07 — The ~36× coinbase claim (plan section 14)\n"
        "Reproduce the proponent's double-spend and sniping break-even tables.",
        "body": """
```python
res = EX.p5_coinbase_claim(cfg)
print("double-spend V/C:", res.data["doublespend_table"])
print("headline 36×:", res.data["headline_36x"])
print("sniping V/C:", res.data["sniping_table"])

fig = PL.fig2_reversal_vs_depth(cfg)
plt.show()
```
""",
    },
    "08_finite_attacks": {
        "title": "# 08 — Finite attack duration and rational quitting (sections 19-21)\n"
        "Deadlines, start-time sensitivity, and abandonment thresholds.",
        "body": """
```python
r1 = EX.r1_finite_duration(cfg, trials=TRIALS)
print("R1:", {k: [round(p["p_hat"], 4) for p in v] for k, v in r1.data["curves"].items()})
r2 = EX.r2_start_time(cfg, trials=TRIALS)
print("R2:", [(s["scenario"], round(s["p_hat"], 4)) for s in r2.data["scenarios"]])
r3 = EX.r3_abandonment(cfg, trials=TRIALS)
print("R3:", [(s["scenario"], round(s["p_hat"], 4)) for s in r3.data["scenarios"]])

fig = PL.fig9_finite_duration(cfg, results={"R1": r1})
plt.show()
```
""",
    },
    "09_external_hash": {
        "title": "# 09 — Temporary external hashpower (sections 22-24)\n"
        "Temporary-majority duration and acquisition delay.",
        "body": """
```python
r4 = EX.r4_temporary_majority(cfg, trials=2000)
r5 = EX.r5_acquisition_delay(cfg, trials=2000)
r6 = EX.r6_external_threshold(cfg)
print("R6 external hash ratio:", r6.data["tables"])

fig = PL.fig10_temporary_majority_heatmap(cfg, results={"R4": r4})
plt.show()
fig = PL.fig11_acquisition_delay_heatmap(cfg, results={"R5": r5})
plt.show()
```
""",
    },
    "10_economics": {
        "title": "# 10 — Economic viability and cost accounting (sections 25-26)\n"
        "Break-even value and cost across confirmation policies.",
        "body": """
```python
r7 = EX.r7_economics(cfg)
r8 = EX.r8_cost_accounting(cfg)
print(r7.frame()[["acceptance_policy", "break_even_value_reward_multiple"]])
print(r8.frame()[["acceptance_policy", "expected_attack_cost"]])

fig = PL.fig12_break_even_vs_policy(cfg)
plt.show()
```
""",
    },
}


def main() -> None:
    NOTEBOOKS.mkdir(parents=True, exist_ok=True)
    for name, spec in SPECS.items():
        path = NOTEBOOKS / f"{name}.ipynb"
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(notebook(spec["title"], spec["body"]), handle, indent=1)
            handle.write("\n")
        print(f"wrote {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()