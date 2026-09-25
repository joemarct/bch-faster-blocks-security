"""Figures 1-12 from plan section 36.

Every function returns a ``matplotlib.figure.Figure``. Each accepts an
optional ``results`` mapping (as returned by ``experiments.run_phase1`` /
``run_phase2``) so a full experiment run is not recomputed just to draw.
When a result is absent the figure falls back to a lighter-weight
computation from the config.

Figures are written under ``config["output"]["figures_dir"]`` by
:func:`save_figure` / :func:`make_all_figures`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import matplotlib


def _in_ipython() -> bool:
    try:
        from IPython import get_ipython
    except ImportError:  # pragma: no cover - IPython is a notebook-only extra
        return False
    return get_ipython() is not None


if not _in_ipython():
    matplotlib.use("Agg")  # headless, deterministic

import matplotlib.pyplot as plt
import numpy as np

from . import analytical as A
from . import economics as EC
from . import experiments as EX

REPO_ROOT = Path(__file__).resolve().parents[1]
_FIG_DPI = 150


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def _figures_dir(cfg: dict[str, Any]) -> Path:
    rel = cfg.get("output", {}).get("figures_dir", "results/figures")
    path = Path(rel)
    if not path.is_absolute():
        path = REPO_ROOT / path
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_figure(fig, name: str, cfg: dict[str, Any], fmt: str = "png") -> Path:
    path = _figures_dir(cfg) / f"{name}.{fmt}"
    fig.savefig(path, dpi=_FIG_DPI, bbox_inches="tight")
    plt.close(fig)
    return path


def _get(results: Mapping[str, EX.ExperimentResult] | None, key: str, name: str) -> Any:
    if results and key in results:
        return results[key]
    return None


# --------------------------------------------------------------------------
# Figure 1: analytical vs Monte Carlo
# --------------------------------------------------------------------------
def fig1_analytical_vs_mc(cfg, results=None, trials: int | None = None):
    res = _get(results, "P1", "P1_validate_simulators") or EX.p1_validate_simulators(
        cfg, trials
    )
    cells = res.data["cells"]
    fig, ax = plt.subplots(figsize=(6, 6))
    xs = np.array([c["analytical"] for c in cells])
    ax.plot([1e-6, 1.0], [1e-6, 1.0], "k--", lw=1, label="y = x")
    for key, label, marker in (
        ("event_p_hat", "event-driven", "o"),
        ("distribution_p_hat", "distribution", "s"),
    ):
        ys = np.array([c[key] for c in cells])
        ax.scatter(xs, ys, s=18, alpha=0.7, marker=marker, label=label)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("analytical reversal probability")
    ax.set_ylabel("Monte Carlo estimate")
    ax.set_title("Figure 1 — analytical vs Monte Carlo")
    ax.legend()
    ax.grid(True, which="both", alpha=0.3)
    return fig


# --------------------------------------------------------------------------
# Figure 2: reversal probability vs confirmation depth
# --------------------------------------------------------------------------
def fig2_reversal_vs_depth(cfg, results=None):
    zs = list(cfg["confirmations"]["default"])
    z_grid = np.arange(1, max(zs) + 3)
    shares = [0.05, 0.10, 0.20, 0.30, 0.40]
    fig, ax = plt.subplots(figsize=(7, 5))
    for q in shares:
        y = [A.nakamoto_reversal_probability(q, int(z)) for z in z_grid]
        ax.plot(z_grid, y, marker="o", ms=3, label=f"q = {q:.2f}")
    ax.set_yscale("log")
    ax.set_xlabel("confirmation depth z")
    ax.set_ylabel("reversal probability")
    ax.set_title("Figure 2 — reversal probability vs confirmation depth")
    ax.legend()
    ax.grid(True, which="both", alpha=0.3)
    return fig


# --------------------------------------------------------------------------
# Figure 3: focused policy comparison
# --------------------------------------------------------------------------
def fig3_focused_policies(cfg, results=None, trials: int | None = None):
    res = _get(results, "P2", "P2_policy_comparison") or EX.p2_policy_comparison(
        cfg, trials=trials
    )
    rows = res.data["rows"]
    labels = [r["policy"] for r in rows]
    y = [r["analytical_reversal_probability"] for r in rows]
    sim = [r["simulated_reversal_probability"] for r in rows]
    x = np.arange(len(labels))
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(x - 0.2, y, width=0.4, label="analytical")
    ax.bar(x + 0.2, sim, width=0.4, label="simulated")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=20, ha="right")
    ax.set_ylabel("reversal probability")
    ax.set_title(f"Figure 3 — focused policy comparison (q = {res.data['q']:.2f})")
    ax.legend()
    ax.grid(True, axis="y", alpha=0.3)
    return fig


# --------------------------------------------------------------------------
# Figure 4: deficit distribution at acceptance
# --------------------------------------------------------------------------
def fig4_deficit_distribution(cfg, results=None):
    res = _get(results, "P3", "P3_decomposition") or EX.p3_decomposition(cfg)
    q = res.data["q"]
    label = "60s × 2" if "60s × 2" in res.data["decomposition"] else next(
        iter(res.data["decomposition"])
    )
    dist = res.data["decomposition"][label]["deficit_distribution"]
    items = sorted(dist.items())
    xs = [k for k, _ in items]
    ys = [v for _, v in items]
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.bar([str(x) for x in xs], ys)
    ax.set_xlabel("attacker deficit at acceptance (−1 = already ahead)")
    ax.set_ylabel("probability")
    ax.set_title(f"Figure 4 — deficit distribution ({label}, q = {q:.2f})")
    ax.grid(True, axis="y", alpha=0.3)
    return fig


# --------------------------------------------------------------------------
# Figure 5: reversal decomposition by deficit
# --------------------------------------------------------------------------
def fig5_decomposition(cfg, results=None):
    res = _get(results, "P3", "P3_decomposition") or EX.p3_decomposition(cfg)
    q = res.data["q"]
    label = "60s × 2" if "60s × 2" in res.data["decomposition"] else next(
        iter(res.data["decomposition"])
    )
    dec = res.data["decomposition"][label]["decomposition"]
    ds = [row[0] for row in dec]
    contrib = [row[3] for row in dec]
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.bar([str(d) for d in ds], contrib)
    ax.set_xlabel("deficit d")
    ax.set_ylabel("contribution P(D=d) · catch-up")
    ax.set_title(f"Figure 5 — reversal decomposition ({label}, q = {q:.2f})")
    ax.grid(True, axis="y", alpha=0.3)
    return fig


# --------------------------------------------------------------------------
# Figure 6: equal expected chainwork
# --------------------------------------------------------------------------
def fig6_equal_chainwork(cfg, results=None, trials: int | None = None):
    res = _get(results, "P6", "P6_equal_chainwork") or EX.p6_equal_chainwork(
        cfg, trials
    )
    rows = res.data["rows"]
    labels = [r["pair"] for r in rows]
    y = [r["analytical"] for r in rows]
    ci = np.clip(
        np.array(
            [[r["analytical"] - r["ci"][0], r["ci"][1] - r["analytical"]] for r in rows]
        ).T,
        0.0,
        None,
    )
    x = np.arange(len(labels))
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.errorbar(x, y, yerr=ci, fmt="o", capsize=4)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=20, ha="right")
    ax.set_yscale("log")
    ax.set_ylabel("reversal probability")
    ax.set_title(f"Figure 6 — equal expected chainwork (q = {res.data['q']:.2f})")
    ax.grid(True, which="both", alpha=0.3)
    return fig


# --------------------------------------------------------------------------
# Figure 7: reversal probability vs elapsed time
# --------------------------------------------------------------------------
def fig7_reversal_vs_time(cfg, results=None, trials: int | None = None):
    res = _get(results, "P7", "P7_equal_elapsed_time") or EX.p7_equal_elapsed_time(
        cfg, trials
    )
    rows = res.data["rows"]
    fig, ax = plt.subplots(figsize=(7, 5))
    for interval in sorted({r["interval_sec"] for r in rows}):
        sub = sorted((r for r in rows if r["interval_sec"] == interval), key=lambda r: r["horizon_sec"])
        xs = [r["horizon_sec"] for r in sub]
        ys = [r["reversal_probability"] for r in sub]
        ax.plot(xs, ys, marker="o", label=f"{int(interval)}s blocks")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("elapsed time since inclusion (s)")
    ax.set_ylabel("reversal probability")
    ax.set_title(f"Figure 7 — reversal vs elapsed time (q = {res.data['q']:.2f})")
    ax.legend()
    ax.grid(True, which="both", alpha=0.3)
    return fig


# --------------------------------------------------------------------------
# Figure 8: security/latency frontier
# --------------------------------------------------------------------------
def fig8_frontier(cfg, results=None, trials: int | None = None):
    res = _get(results, "P8", "P8_frontier") or EX.p8_frontier(cfg, trials)
    curves = res.data["curves"]
    fig, ax = plt.subplots(figsize=(7, 5))
    for q, payload in curves.items():
        for family in ("600s", "60s"):
            pts = [p for p in payload["points"] if p["family"] == family]
            xs = [p["median_latency_sec"] for p in pts]
            ys = [p["reversal_probability"] for p in pts]
            ax.plot(xs, ys, marker="o", ms=3, label=f"q={q:.2f}, {family}")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("median confirmation latency (s)")
    ax.set_ylabel("reversal probability")
    ax.set_title("Figure 8 — security/latency frontier")
    ax.legend(fontsize=7, ncol=2)
    ax.grid(True, which="both", alpha=0.3)
    return fig


# --------------------------------------------------------------------------
# Figure 9: finite attack duration curves
# --------------------------------------------------------------------------
def fig9_finite_duration(cfg, results=None, trials: int | None = None):
    res = _get(results, "R1", "R1_finite_duration") or EX.r1_finite_duration(
        cfg, trials
    )
    curves = res.data["curves"]
    fig, ax = plt.subplots(figsize=(7, 5))
    for label, points in curves.items():
        xs = [p["deadline_sec"] for p in points]
        ys = [p["p_hat"] for p in points]
        ax.plot(xs, ys, marker="o", ms=3, label=label)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("attack deadline (s)")
    ax.set_ylabel("P(success before deadline)")
    ax.set_title(f"Figure 9 — finite attack duration (q = {res.data['q']:.2f})")
    ax.legend(fontsize=8)
    ax.grid(True, which="both", alpha=0.3)
    return fig


# --------------------------------------------------------------------------
# Figure 10: temporary-majority duration heatmap
# --------------------------------------------------------------------------
def fig10_temporary_majority_heatmap(cfg, results=None, trials: int | None = None):
    res = _get(results, "R4", "R4_temporary_majority") or EX.r4_temporary_majority(
        cfg, trials
    )
    heat = res.data["heat"]
    fig, ax = plt.subplots(figsize=(7, 5))
    im = ax.imshow(heat, aspect="auto", origin="lower", cmap="magma")
    ax.set_xticks(range(len(res.data["durations"])))
    ax.set_xticklabels([f"{int(d)}" for d in res.data["durations"]], rotation=30, ha="right")
    ax.set_yticks(range(len(res.data["shares"])))
    ax.set_yticklabels([f"{s:.2f}" for s in res.data["shares"]])
    ax.set_xlabel("active duration (s)")
    ax.set_ylabel("active attacker share")
    ax.set_title("Figure 10 — temporary majority duration")
    fig.colorbar(im, ax=ax, label="reversal probability")
    return fig


# --------------------------------------------------------------------------
# Figure 11: acquisition-delay heatmap
# --------------------------------------------------------------------------
def fig11_acquisition_delay_heatmap(cfg, results=None, trials: int | None = None):
    res = _get(results, "R5", "R5_acquisition_delay") or EX.r5_acquisition_delay(
        cfg, trials
    )
    heat = res.data["heat"]
    fig, ax = plt.subplots(figsize=(7, 5))
    im = ax.imshow(heat, aspect="auto", origin="lower", cmap="viridis")
    ax.set_xticks(range(len(res.data["shares"])))
    ax.set_xticklabels([f"{s:.2f}" for s in res.data["shares"]])
    ax.set_yticks(range(len(res.data["delays"])))
    ax.set_yticklabels([f"{int(d)}" for d in res.data["delays"]])
    ax.set_xlabel("active attacker share")
    ax.set_ylabel("acquisition delay (s)")
    ax.set_title("Figure 11 — external-hash acquisition delay")
    fig.colorbar(im, ax=ax, label="reversal probability")
    return fig


# --------------------------------------------------------------------------
# Figure 12: break-even transaction value vs confirmation policy
# --------------------------------------------------------------------------
def fig12_break_even_vs_policy(cfg, results=None):
    q = float(cfg["attacker_shares"]["primary"])
    policies = list(cfg["confirmations"]["policies"])
    labels = [f"{int(p['interval_sec'])}s×{int(p['confirmations'])}" for p in policies]
    multiples = [
        A.doublespend_break_even_multiple(q, int(p["confirmations"])) for p in policies
    ]
    fig, ax = plt.subplots(figsize=(8, 5))
    x = np.arange(len(labels))
    ax.bar(x, multiples)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=20, ha="right")
    ax.set_ylabel("break-even value / coinbase")
    ax.set_title(f"Figure 12 — break-even transaction value (q = {q:.2f})")
    ax.grid(True, axis="y", alpha=0.3)
    return fig


# --------------------------------------------------------------------------
# Driver
# --------------------------------------------------------------------------
FIGURES = {
    "fig01_analytical_vs_mc": fig1_analytical_vs_mc,
    "fig02_reversal_vs_depth": fig2_reversal_vs_depth,
    "fig03_focused_policies": fig3_focused_policies,
    "fig04_deficit_distribution": fig4_deficit_distribution,
    "fig05_decomposition": fig5_decomposition,
    "fig06_equal_chainwork": fig6_equal_chainwork,
    "fig07_reversal_vs_time": fig7_reversal_vs_time,
    "fig08_frontier": fig8_frontier,
    "fig09_finite_duration": fig9_finite_duration,
    "fig10_temporary_majority_heatmap": fig10_temporary_majority_heatmap,
    "fig11_acquisition_delay_heatmap": fig11_acquisition_delay_heatmap,
    "fig12_break_even_vs_policy": fig12_break_even_vs_policy,
}


def make_all_figures(
    cfg: dict[str, Any] | None = None,
    results: Mapping[str, EX.ExperimentResult] | None = None,
    trials: int | None = None,
    only: list[str] | None = None,
) -> dict[str, Path]:
    """Render all (or a subset of) figures and return name -> path."""
    cfg = cfg or EX.load_config()
    written: dict[str, Path] = {}
    for name, fn in FIGURES.items():
        if only and name not in only:
            continue
        try:
            fig = fn(cfg, results=results, trials=trials)
        except TypeError:
            fig = fn(cfg, results=results)
        written[name] = save_figure(fig, name, cfg)
    return written


__all__ = ["make_all_figures", "save_figure", "FIGURES"] + list(FIGURES)