"""Experiment orchestration for Phases I and II (plan sections 9-26, 36-40).

Each ``p*`` / ``r*`` function runs one experiment and returns an
:class:`ExperimentResult`: a list of machine-readable :class:`ResultRecord`
rows plus a ``data`` dictionary with the richer arrays that ``plotting.py``
needs (distributions, grids, curves). Nothing here draws figures; nothing
here hard-codes a number that belongs in ``config/defaults.yaml``.

Experiments are deterministic given ``(config, master seed, code_version)``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np
import pandas as pd

from . import analytical as A
from . import attacks as AT
from . import economics as EC
from . import external_hash as XH
from . import mining as MN
from . import stone_dp as SD
from .statistics import (
    MASTER_FIELDS,
    ResultRecord,
    code_version,
    records_to_frame,
    wilson_upper_bound,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = REPO_ROOT / "config" / "defaults.yaml"


# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------
def load_config(path: str | Path | None = None) -> dict[str, Any]:
    """Load the YAML configuration (defaults to ``config/defaults.yaml``)."""
    import yaml

    cfg_path = Path(path) if path is not None else DEFAULT_CONFIG_PATH
    with open(cfg_path, "r", encoding="utf-8") as handle:
        cfg = yaml.safe_load(handle)
    if not isinstance(cfg, dict):
        raise ValueError(f"config did not parse to a mapping: {cfg_path}")
    return cfg


def master_seed(cfg: dict[str, Any]) -> int:
    return int(cfg["seed"]["master"])


# --------------------------------------------------------------------------
# Result container
# --------------------------------------------------------------------------
@dataclass
class ExperimentResult:
    """Records (CSV-facing) plus rich arrays (plot-facing) for one experiment."""

    name: str
    phase: str
    records: list[ResultRecord] = field(default_factory=list)
    data: dict[str, Any] = field(default_factory=dict)

    def frame(self) -> pd.DataFrame:
        return records_to_frame(self.records)


def _result(name: str, phase: str) -> ExperimentResult:
    return ExperimentResult(name=name, phase=phase)


def _policy_label(interval_sec: float, z: int) -> str:
    return f"{int(interval_sec)}s × {z}"


def _wait_stats(z: int, interval_sec: float) -> dict[str, float]:
    p50 = A.median_wait_sec(z, interval_sec)
    quantiles = A.wait_time_quantiles(z, interval_sec, (0.05, 0.5, 0.95))
    return {
        "expected_wait_sec": A.expected_wait_sec(z, interval_sec),
        "median_wait_sec": p50,
        "p05_wait_sec": quantiles[0],
        "p95_wait_sec": quantiles[2],
    }


def _sim_record(
    *,
    experiment: str,
    phase: str,
    model: str,
    q: float,
    z: int,
    interval_sec: float,
    sim: MN.ReversalSimResult,
    acceptance_policy: str = "",
    tie_policy: str = "tie_win",
    expected_work: float | None = None,
    extra: dict[str, Any] | None = None,
) -> ResultRecord:
    """Build a master-schema row from a simulator result."""
    wait = _wait_stats(z, interval_sec)
    record = ResultRecord(
        experiment=experiment,
        phase=phase,
        model=model,
        target_interval_sec=float(interval_sec),
        attacker_share=float(q),
        confirmations=int(z),
        acceptance_policy=acceptance_policy or _policy_label(interval_sec, z),
        expected_wait_sec=wait["expected_wait_sec"],
        mean_wait_sec=wait["expected_wait_sec"],
        median_wait_sec=wait["median_wait_sec"],
        expected_work=expected_work
        if expected_work is not None
        else A.normalized_work(z, interval_sec),
        mean_realized_work=A.normalized_work(z, interval_sec),
        tie_policy=tie_policy,
        trials=sim.trials,
        successes=sim.successes,
        success_probability=sim.p_hat,
        ci_lower=sim.ci_lower,
        ci_upper=sim.ci_upper,
        mean_attack_duration_sec=sim.mean_acceptance_blocks * interval_sec,
        seed=sim.seed,
        code_version=code_version(REPO_ROOT),
    )
    record.extra["p05_wait_sec"] = wait["p05_wait_sec"]
    record.extra["p95_wait_sec"] = wait["p95_wait_sec"]
    record.extra["mean_deficit_at_acceptance"] = sim.mean_deficit_at_acceptance
    record.extra["mean_attacker_blocks_at_acceptance"] = sim.mean_attacker_blocks_at_acceptance
    if extra:
        record.extra.update(extra)
    return record


def _tie_policies(cfg: dict[str, Any]) -> list[str]:
    return list(cfg["tie_policies"])


# ==========================================================================
# PHASE I --- REPRODUCTION
# ==========================================================================
def p0_analytical_baseline(cfg: dict[str, Any]) -> ExperimentResult:
    """P0 (section 9): analytical reversal probabilities over (q, z, tie)."""
    res = _result("P0_analytical_baseline", "I")
    shares = list(cfg["attacker_shares"]["sweep"])
    zs = list(cfg["confirmations"]["default"])
    exact: dict[tuple[float, int, str], float] = {}
    poisson: dict[tuple[float, int, str], float] = {}
    for q in shares:
        for z in zs:
            for tie in _tie_policies(cfg):
                e = A.nakamoto_reversal_probability(q, z, tie)
                p = A.nakamoto_reversal_probability_poisson(q, z, tie)
                exact[(q, z, tie)] = e
                poisson[(q, z, tie)] = p
                for model, value in (("analytical_exact", e), ("analytical_poisson", p)):
                    rec = ResultRecord(
                        experiment="P0_analytical_baseline",
                        phase="I",
                        model=model,
                        attacker_share=float(q),
                        confirmations=int(z),
                        acceptance_policy=_policy_label(600.0, z),
                        tie_policy=tie,
                        success_probability=value,
                        code_version=code_version(REPO_ROOT),
                    )
                    res.records.append(rec)
    res.data = {"shares": shares, "zs": zs, "exact": exact, "poisson": poisson}
    return res


def p1_validate_simulators(
    cfg: dict[str, Any], trials: int | None = None
) -> ExperimentResult:
    """P1 (section 10): MC (event + distribution) vs analytical."""
    res = _result("P1_validate_simulators", "I")
    trials = int(trials if trials is not None else cfg["monte_carlo"]["dev_trials"])
    shares = list(cfg["attacker_shares"]["coarse"])
    zs = list(cfg["confirmations"]["default"])
    seed = master_seed(cfg)
    cells: list[dict[str, Any]] = []
    for q in shares:
        for z in zs:
            for tie in _tie_policies(cfg):
                analytic = A.nakamoto_reversal_probability(q, z, tie)
                event = MN.simulate_reversal_bernoulli(
                    q, z, tie_policy=tie, trials=trials, master_seed=seed,
                    seed_label="p1_event",
                )
                dist = MN.simulate_reversal_distribution(
                    q, z, tie_policy=tie, trials=trials, master_seed=seed,
                    seed_label="p1_dist",
                )
                for model, sim in (("event_bernoulli", event), ("distribution", dist)):
                    rec = _sim_record(
                        experiment="P1_validate_simulators", phase="I", model=model,
                        q=q, z=z, interval_sec=600.0, sim=sim, tie_policy=tie,
                    )
                    rec.extra["analytical_reversal_probability"] = analytic
                    rec.extra["abs_error"] = abs(sim.p_hat - analytic)
                    res.records.append(rec)
                cells.append(
                    {
                        "q": q, "z": z, "tie_policy": tie,
                        "analytical": analytic,
                        "event_p_hat": event.p_hat,
                        "event_ci": (event.ci_lower, event.ci_upper),
                        "distribution_p_hat": dist.p_hat,
                        "distribution_ci": (dist.ci_lower, dist.ci_upper),
                        "within_ci": (
                            event.ci_lower <= analytic <= event.ci_upper
                            and dist.ci_lower <= analytic <= dist.ci_upper
                        ),
                    }
                )
    res.data = {"trials": trials, "cells": cells}
    return res


def p2_policy_comparison(
    cfg: dict[str, Any],
    q: float | None = None,
    trials: int | None = None,
) -> ExperimentResult:
    """P2 (section 11): 2x60s vs 1x600s, plus deeper 60s policies."""
    res = _result("P2_policy_comparison", "I")
    q = float(q if q is not None else cfg["attacker_shares"]["primary"])
    trials = int(trials if trials is not None else cfg["monte_carlo"]["dev_trials"])
    seed = master_seed(cfg)
    policies = list(cfg["confirmations"]["policies"])
    deadlines = [600.0, 3600.0]
    rows: list[dict[str, Any]] = []
    for policy in policies:
        interval = float(policy["interval_sec"])
        z = int(policy["confirmations"])
        tie = "tie_win"
        sim = MN.simulate_reversal_distribution(
            q, z, tie_policy=tie, interval_sec=interval, trials=trials,
            master_seed=seed, seed_label="p2_policy",
        )
        analytic = A.nakamoto_reversal_probability(q, z, tie)
        rec = _sim_record(
            experiment="P2_policy_comparison", phase="I", model="distribution",
            q=q, z=z, interval_sec=interval, sim=sim, tie_policy=tie,
        )
        rec.extra["analytical_reversal_probability"] = analytic
        finite: dict[float, float] = {}
        for deadline in deadlines:
            fh = AT.finite_horizon_reversal(
                q, z, deadline, interval_sec=interval, tie_policy=tie,
                trials=trials, master_seed=seed, seed_label="p2_finite",
            )
            finite[deadline] = fh.p_hat
            rec.extra[f"finite_{int(deadline)}s_success_probability"] = fh.p_hat
        res.records.append(rec)
        rows.append(
            {
                "policy": _policy_label(interval, z),
                "interval_sec": interval,
                "confirmations": z,
                "expected_wait_sec": A.expected_wait_sec(z, interval),
                "median_wait_sec": A.median_wait_sec(z, interval),
                "expected_normalized_work": A.normalized_work(z, interval),
                "analytical_reversal_probability": analytic,
                "simulated_reversal_probability": sim.p_hat,
                "ci_lower": sim.ci_lower,
                "ci_upper": sim.ci_upper,
                "mean_deficit_at_acceptance": sim.mean_deficit_at_acceptance,
                "finite_10min_success_probability": finite[600.0],
                "finite_1h_success_probability": finite[3600.0],
            }
        )
    res.data = {"q": q, "trials": trials, "rows": rows}
    return res


def p3_decomposition(cfg: dict[str, Any], q: float | None = None) -> ExperimentResult:
    """P3 (section 12): deficit distribution and reversal decomposition."""
    res = _result("P3_decomposition", "I")
    q = float(q if q is not None else cfg["attacker_shares"]["primary"])
    policies = list(cfg["confirmations"]["policies"])
    decomposition: dict[str, Any] = {}
    for policy in policies:
        interval = float(policy["interval_sec"])
        z = int(policy["confirmations"])
        label = _policy_label(interval, z)
        dist = A.attacker_deficit_distribution(q, z)
        dec = A.reversal_decomposition(q, z, "tie_win")
        decomposition[label] = {
            "deficit_distribution": dist,
            "decomposition": dec,
            "reversal_probability": A.nakamoto_reversal_probability(q, z, "tie_win"),
        }
        for d, prow, cu, contrib in dec:
            rec = ResultRecord(
                experiment="P3_decomposition", phase="I", model="analytical_decomposition",
                attacker_share=q, confirmations=z, acceptance_policy=label,
                tie_policy="tie_win", success_probability=contrib,
                code_version=code_version(REPO_ROOT),
            )
            rec.extra["deficit"] = d
            rec.extra["deficit_probability"] = prow
            rec.extra["catchup_probability"] = cu
            res.records.append(rec)
    res.data = {"q": q, "decomposition": decomposition}
    return res


def p4_interval_comparison(cfg: dict[str, Any], trials: int | None = None) -> ExperimentResult:
    """P4 (section 13): same z, different target interval T."""
    res = _result("P4_interval_comparison", "I")
    trials = int(trials if trials is not None else cfg["monte_carlo"]["dev_trials"])
    seed = master_seed(cfg)
    q = float(cfg["attacker_shares"]["primary"])
    intervals = [cfg["intervals"]["baseline_sec"], cfg["intervals"]["fast_sec"]]
    zs = list(cfg["confirmations"]["default"])
    cells: list[dict[str, Any]] = []
    for z in zs:
        for interval in intervals:
            sim = MN.simulate_reversal_distribution(
                q, z, interval_sec=float(interval), trials=trials,
                master_seed=seed, seed_label="p4",
            )
            analytic = A.nakamoto_reversal_probability(q, z)
            rec = _sim_record(
                experiment="P4_interval_comparison", phase="I", model="distribution",
                q=q, z=z, interval_sec=float(interval), sim=sim,
            )
            rec.extra["analytical_reversal_probability"] = analytic
            res.records.append(rec)
            cells.append(
                {
                    "z": z, "interval_sec": float(interval),
                    "analytical": analytic, "p_hat": sim.p_hat,
                    "ci": (sim.ci_lower, sim.ci_upper),
                }
            )
    res.data = {"q": q, "trials": trials, "cells": cells}
    return res


def p5_coinbase_claim(cfg: dict[str, Any]) -> ExperimentResult:
    """P5 (section 14): reproduce the ~36x coinbase break-even claim."""
    res = _result("P5_coinbase_claim", "I")
    q = float(cfg["attacker_shares"]["primary"])
    ms = [1, 2, 3, 4, 5, 10]
    ds_table = EC.doublespend_break_even_table(q, ms)
    sniping_pairs = [(1, 1), (1, 2), (2, 2), (2, 3), (3, 5), (5, 10)]
    sn_table = EC.sniping_break_even_table(q, sniping_pairs)
    for m, value in ds_table.items():
        rec = ResultRecord(
            experiment="P5_coinbase_claim", phase="I", model="doublespend_break_even",
            attacker_share=q, confirmations=int(m),
            success_probability=A.race_probability(q, m, m),
            break_even_value_reward_multiple=value,
            code_version=code_version(REPO_ROOT),
        )
        rec.extra["confirmation_requirement_m_minus_1"] = m - 1
        res.records.append(rec)
    for (n, m), value in sn_table.items():
        rec = ResultRecord(
            experiment="P5_coinbase_claim", phase="I", model="sniping_break_even",
            attacker_share=q, confirmations=int(m),
            success_probability=A.race_probability(q, n + m, m),
            break_even_value_reward_multiple=value,
            code_version=code_version(REPO_ROOT),
        )
        rec.extra["n_behind"] = n
        rec.extra["m_needed"] = m
        res.records.append(rec)
    res.data = {
        "q": q,
        "doublespend_table": ds_table,
        "sniping_table": sn_table,
        "headline_36x": ds_table.get(2),
    }
    return res


def p6_equal_chainwork(cfg: dict[str, Any], trials: int | None = None) -> ExperimentResult:
    """P6 (section 15): equal expected chainwork, different intervals."""
    res = _result("P6_equal_chainwork", "I")
    trials = int(trials if trials is not None else cfg["monte_carlo"]["dev_trials"])
    seed = master_seed(cfg)
    q = float(cfg["attacker_shares"]["primary"])
    base = float(cfg["intervals"]["baseline_sec"])
    fast = float(cfg["intervals"]["fast_sec"])
    ratio = int(base / fast)
    pairs = [(z, z * ratio) for z in (1, 2, 3)]
    rows: list[dict[str, Any]] = []
    for z_base, z_fast in pairs:
        for interval, z in ((base, z_base), (fast, z_fast)):
            sim = MN.simulate_reversal_distribution(
                q, z, interval_sec=interval, trials=trials,
                master_seed=seed, seed_label="p6",
            )
            analytic = A.nakamoto_reversal_probability(q, z)
            rec = _sim_record(
                experiment="P6_equal_chainwork", phase="I", model="distribution",
                q=q, z=z, interval_sec=interval, sim=sim,
            )
            rec.extra["analytical_reversal_probability"] = analytic
            rec.extra["equal_chainwork_pair"] = f"{z_base}x{int(base)}s vs {z_fast}x{int(fast)}s"
            res.records.append(rec)
            rows.append(
                {
                    "pair": f"{int(base)}s×{z_base} vs {int(fast)}s×{z_fast}",
                    "interval_sec": interval, "z": z,
                    "expected_work": A.normalized_work(z, interval),
                    "analytical": analytic, "p_hat": sim.p_hat,
                    "ci": (sim.ci_lower, sim.ci_upper),
                }
            )
    res.data = {"q": q, "trials": trials, "rows": rows, "pairs": pairs}
    return res


def p7_equal_elapsed_time(cfg: dict[str, Any], trials: int | None = None) -> ExperimentResult:
    """P7 (section 16): condition on wall-clock time, not confirmations."""
    res = _result("P7_equal_elapsed_time", "I")
    trials = int(trials if trials is not None else cfg["monte_carlo"]["dev_trials"])
    seed = master_seed(cfg)
    q = float(cfg["attacker_shares"]["primary"])
    horizons = [60, 120, 180, 300, 600, 900, 1200, 1800, 3600]
    intervals = [cfg["intervals"]["baseline_sec"], cfg["intervals"]["fast_sec"]]
    rng = np.random.default_rng(seed)
    rows: list[dict[str, Any]] = []
    for horizon in horizons:
        for interval in intervals:
            interval = float(interval)
            total_blocks = rng.poisson(horizon / interval, size=trials)
            expected_blocks = horizon / interval
            # Reversal within the horizon, measured from inclusion (z=1).
            fh = AT.finite_horizon_reversal(
                q, 1, float(horizon), interval_sec=interval, tie_policy="tie_win",
                trials=trials, master_seed=seed, seed_label="p7",
            )
            rec = ResultRecord(
                experiment="P7_equal_elapsed_time", phase="I", model="finite_horizon",
                target_interval_sec=interval, attacker_share=q, confirmations=1,
                acceptance_policy=f"1 conf, {interval:.0f}s",
                attack_deadline_sec=float(horizon), tie_policy="tie_win",
                trials=trials, successes=fh.successes, success_probability=fh.p_hat,
                ci_lower=fh.ci_lower, ci_upper=fh.ci_upper, seed=fh.seed,
                code_version=code_version(REPO_ROOT),
            )
            rec.extra["expected_blocks_in_horizon"] = expected_blocks
            rec.extra["mean_blocks_in_horizon"] = float(total_blocks.mean())
            rec.extra["expected_work_in_horizon"] = A.normalized_work(1, interval) * expected_blocks
            res.records.append(rec)
            rows.append(
                {
                    "horizon_sec": horizon, "interval_sec": interval,
                    "expected_blocks": expected_blocks,
                    "expected_work": A.normalized_work(1, interval) * expected_blocks,
                    "reversal_probability": fh.p_hat,
                    "ci": (fh.ci_lower, fh.ci_upper),
                }
            )
    res.data = {"q": q, "trials": trials, "rows": rows, "horizons": horizons}
    return res


def p8_frontier(cfg: dict[str, Any], trials: int | None = None) -> ExperimentResult:
    """P8 (section 17): security/latency frontier per q."""
    res = _result("P8_frontier", "I")
    trials = int(trials if trials is not None else cfg["monte_carlo"]["dev_trials"])
    seed = master_seed(cfg)
    shares = [0.05, 0.10, 0.20, 0.30, 0.40]
    zs = list(cfg["confirmations"]["default"])
    curves: dict[float, dict[str, Any]] = {}
    for q in shares:
        points: list[dict[str, Any]] = []
        for interval, tag in ((600.0, "600s"), (60.0, "60s")):
            for z in zs:
                sim = MN.simulate_reversal_distribution(
                    q, z, interval_sec=interval, trials=trials,
                    master_seed=seed, seed_label="p8",
                )
                analytic = A.nakamoto_reversal_probability(q, z)
                rec = _sim_record(
                    experiment="P8_frontier", phase="I", model="distribution",
                    q=q, z=z, interval_sec=interval, sim=sim,
                )
                rec.extra["analytical_reversal_probability"] = analytic
                rec.extra["family"] = tag
                res.records.append(rec)
                points.append(
                    {
                        "family": tag, "interval_sec": interval, "z": z,
                        "expected_latency_sec": A.expected_wait_sec(z, interval),
                        "median_latency_sec": A.median_wait_sec(z, interval),
                        "reversal_probability": sim.p_hat,
                        "ci": (sim.ci_lower, sim.ci_upper),
                    }
                )
        curves[q] = {"points": points}
    res.data = {"shares": shares, "trials": trials, "curves": curves}
    return res


def mvp_table(cfg: dict[str, Any], trials: int | None = None) -> ExperimentResult:
    """Section 39 minimum-viable table at q = 0.10."""
    return p2_policy_comparison(cfg, trials=trials)


def run_phase1(cfg: dict[str, Any], trials: int | None = None) -> dict[str, ExperimentResult]:
    """Run P0-P8 in the plan's execution order."""
    return {
        "P0": p0_analytical_baseline(cfg),
        "P1": p1_validate_simulators(cfg, trials),
        "P2": p2_policy_comparison(cfg, trials=trials),
        "P3": p3_decomposition(cfg),
        "P4": p4_interval_comparison(cfg, trials),
        "P5": p5_coinbase_claim(cfg),
        "P6": p6_equal_chainwork(cfg, trials),
        "P7": p7_equal_elapsed_time(cfg, trials),
        "P8": p8_frontier(cfg, trials),
    }


# ==========================================================================
# PHASE II --- ROBUSTNESS
# ==========================================================================
def r1_finite_duration(cfg: dict[str, Any], trials: int | None = None) -> ExperimentResult:
    """R1 (section 19): success before a finite deadline."""
    res = _result("R1_finite_duration", "II")
    trials = int(trials if trials is not None else cfg["monte_carlo"]["dev_trials"])
    seed = master_seed(cfg)
    q = float(cfg["attacker_shares"]["primary"])
    deadlines = list(cfg["deadlines_sec"])
    policies = list(cfg["confirmations"]["policies"])
    curves: dict[str, list[dict[str, Any]]] = {}
    for policy in policies:
        interval = float(policy["interval_sec"])
        z = int(policy["confirmations"])
        label = _policy_label(interval, z)
        eventual = A.nakamoto_reversal_probability(q, z, "tie_win")
        points: list[dict[str, Any]] = []
        for deadline in deadlines:
            fh = AT.finite_horizon_reversal(
                q, z, float(deadline), interval_sec=interval, tie_policy="tie_win",
                trials=trials, master_seed=seed, seed_label="r1",
            )
            rec = ResultRecord(
                experiment="R1_finite_duration", phase="II", model="finite_horizon",
                target_interval_sec=interval, attacker_share=q, confirmations=z,
                acceptance_policy=label, attack_deadline_sec=float(deadline),
                tie_policy="tie_win", trials=trials, successes=fh.successes,
                success_probability=fh.p_hat, ci_lower=fh.ci_lower,
                ci_upper=fh.ci_upper, seed=fh.seed,
                code_version=code_version(REPO_ROOT),
            )
            rec.extra["eventual_reversal_probability"] = eventual
            rec.extra["mean_steps_taken"] = fh.extra.get("mean_steps_taken")
            res.records.append(rec)
            points.append(
                {
                    "deadline_sec": float(deadline), "p_hat": fh.p_hat,
                    "ci": (fh.ci_lower, fh.ci_upper),
                }
            )
        curves[label] = points
    res.data = {"q": q, "trials": trials, "deadlines": deadlines, "curves": curves}
    return res


def r2_start_time(cfg: dict[str, Any], trials: int | None = None) -> ExperimentResult:
    """R2 (section 20): start-time sensitivity."""
    res = _result("R2_start_time", "II")
    trials = int(trials if trials is not None else cfg["monte_carlo"]["dev_trials"])
    seed = master_seed(cfg)
    q = float(cfg["attacker_shares"]["primary"])
    z = 2
    interval = float(cfg["intervals"]["fast_sec"])
    deadline = float(cfg["deadlines_sec"][-1])
    scenarios: list[dict[str, Any]] = []

    def _add(label: str, **kwargs: Any) -> None:
        fh = AT.finite_horizon_reversal(
            q, z, deadline, interval_sec=interval, tie_policy="tie_win",
            trials=trials, master_seed=seed, seed_label="r2", **kwargs,
        )
        rec = ResultRecord(
            experiment="R2_start_time", phase="II", model="finite_horizon",
            target_interval_sec=interval, attacker_share=q, confirmations=z,
            acceptance_policy=_policy_label(interval, z),
            attack_start_policy=kwargs.get("start_policy", "simultaneous"),
            attack_deadline_sec=deadline, tie_policy="tie_win",
            trials=trials, successes=fh.successes, success_probability=fh.p_hat,
            ci_lower=fh.ci_lower, ci_upper=fh.ci_upper, seed=fh.seed,
            code_version=code_version(REPO_ROOT),
        )
        rec.extra["start_delay_sec"] = kwargs.get("start_delay_sec", 0.0)
        rec.extra["premining_lead"] = kwargs.get("premining_lead", 0)
        rec.extra["scenario"] = label
        res.records.append(rec)
        scenarios.append({"scenario": label, "p_hat": fh.p_hat,
                          "ci": (fh.ci_lower, fh.ci_upper)})

    _add("simultaneous", start_policy="simultaneous")
    _add("at_inclusion", start_policy="at_inclusion")
    for delay in [0, 10, 30, 60, 120, 300, 600]:
        _add(f"reactive_{delay}s", start_policy="reactive", start_delay_sec=float(delay))
    for lead in [-3, -2, -1, 0, 1, 2, 3]:
        _add(f"premining_{lead:+d}", start_policy="premining", premining_lead=lead)
    res.data = {"q": q, "z": z, "interval_sec": interval, "deadline_sec": deadline,
                "trials": trials, "scenarios": scenarios}
    return res


def r3_abandonment(cfg: dict[str, Any], trials: int | None = None) -> ExperimentResult:
    """R3 (section 21): rational attacker abandonment at a deficit."""
    res = _result("R3_abandonment", "II")
    trials = int(trials if trials is not None else cfg["monte_carlo"]["dev_trials"])
    seed = master_seed(cfg)
    q = float(cfg["attacker_shares"]["primary"])
    z = 2
    interval = float(cfg["intervals"]["fast_sec"])
    deadline = float(cfg["deadlines_sec"][-1])
    scenarios: list[dict[str, Any]] = []

    def _add(label: str, abandonment_deficit: int | None, policy: str) -> None:
        fh = AT.finite_horizon_reversal(
            q, z, deadline, interval_sec=interval, tie_policy="tie_win",
            abandonment_deficit=abandonment_deficit,
            trials=trials, master_seed=seed, seed_label="r3",
        )
        rec = ResultRecord(
            experiment="R3_abandonment", phase="II", model="finite_horizon",
            target_interval_sec=interval, attacker_share=q, confirmations=z,
            acceptance_policy=_policy_label(interval, z), attack_deadline_sec=deadline,
            abandonment_policy=policy, tie_policy="tie_win", trials=trials,
            successes=fh.successes, success_probability=fh.p_hat,
            ci_lower=fh.ci_lower, ci_upper=fh.ci_upper, seed=fh.seed,
            code_version=code_version(REPO_ROOT),
        )
        rec.extra["abandonment_deficit"] = abandonment_deficit
        rec.extra["scenario"] = label
        res.records.append(rec)
        scenarios.append({"scenario": label, "p_hat": fh.p_hat,
                          "ci": (fh.ci_lower, fh.ci_upper)})

    _add("never", None, "never")
    for cutoff in [1, 2, 3, 5, 10, 20, 50]:
        _add(f"abandon_at_{cutoff}", cutoff, f"deficit_{cutoff}")
    res.data = {"q": q, "z": z, "interval_sec": interval, "deadline_sec": deadline,
                "trials": trials, "scenarios": scenarios}
    return res


def r4_temporary_majority(cfg: dict[str, Any], trials: int | None = None) -> ExperimentResult:
    """R4 (section 22): temporary-majority duration heatmap."""
    res = _result("R4_temporary_majority", "II")
    grid_trials = int(
        trials if trials is not None else cfg["monte_carlo"].get("grid_trials", 20_000)
    )
    seed = master_seed(cfg)
    q = float(cfg["attacker_shares"]["primary"])
    z = int(cfg["confirmations"]["default"][1]) if len(cfg["confirmations"]["default"]) > 1 else 2
    interval = float(cfg["intervals"]["baseline_sec"])
    deadline = float(cfg["deadlines_sec"][-1])
    shares = [0.05, 0.10, 0.20, 0.33, 0.40, 0.50, 0.60]
    durations = [0, 60, 300, 600, 1800, 3600, 21600, 86400]
    grid = XH.temporary_majority_grid(
        q, shares, [float(d) for d in durations], z, deadline,
        interval_sec=interval, trials=grid_trials, master_seed=seed,
    )
    heat = np.zeros((len(shares), len(durations)))
    for i, share in enumerate(shares):
        for j, duration in enumerate(durations):
            gh = grid[(share, float(duration))]
            heat[i, j] = gh.p_hat
            rec = ResultRecord(
                experiment="R4_temporary_majority", phase="II", model="external_hash",
                target_interval_sec=interval, attacker_share=q, confirmations=z,
                external_hash_share=float(share),
                external_hash_duration_sec=float(duration),
                attack_deadline_sec=deadline, tie_policy="tie_win",
                trials=gh.trials, successes=gh.successes,
                success_probability=gh.p_hat, ci_lower=gh.ci_lower,
                ci_upper=gh.ci_upper, seed=gh.seed,
                code_version=code_version(REPO_ROOT),
            )
            res.records.append(rec)
    res.data = {"q0": q, "z": z, "interval_sec": interval, "deadline_sec": deadline,
                "shares": shares, "durations": durations, "heat": heat,
                "trials": grid_trials}
    return res


def r5_acquisition_delay(cfg: dict[str, Any], trials: int | None = None) -> ExperimentResult:
    """R5 (section 23): acquisition-delay heatmap."""
    res = _result("R5_acquisition_delay", "II")
    grid_trials = int(
        trials if trials is not None else cfg["monte_carlo"].get("grid_trials", 20_000)
    )
    seed = master_seed(cfg)
    q = float(cfg["attacker_shares"]["primary"])
    z = 2
    interval = float(cfg["intervals"]["baseline_sec"])
    deadline = float(cfg["deadlines_sec"][-1])
    shares = [0.10, 0.20, 0.33, 0.40, 0.50]
    delays = [0, 60, 300, 600, 1800, 3600]
    duration = 3600.0
    grid = XH.acquisition_delay_grid(
        q, shares, [float(d) for d in delays], duration, z, deadline,
        interval_sec=interval, trials=grid_trials, master_seed=seed,
    )
    heat = np.zeros((len(delays), len(shares)))
    for i, delay in enumerate(delays):
        for j, share in enumerate(shares):
            gh = grid[(float(delay), share)]
            heat[i, j] = gh.p_hat
            rec = ResultRecord(
                experiment="R5_acquisition_delay", phase="II", model="external_hash",
                target_interval_sec=interval, attacker_share=q, confirmations=z,
                external_hash_share=float(share),
                external_hash_delay_sec=float(delay),
                external_hash_duration_sec=duration,
                attack_deadline_sec=deadline, tie_policy="tie_win",
                trials=gh.trials, successes=gh.successes,
                success_probability=gh.p_hat, ci_lower=gh.ci_lower,
                ci_upper=gh.ci_upper, seed=gh.seed,
                code_version=code_version(REPO_ROOT),
            )
            res.records.append(rec)
    res.data = {"q0": q, "z": z, "interval_sec": interval, "duration_sec": duration,
                "deadline_sec": deadline, "shares": shares, "delays": delays,
                "heat": heat, "trials": grid_trials}
    return res


def _share_for_target(z: int, target: float, tie_policy: str = "tie_win") -> float:
    """Smallest total attacker share whose reversal probability reaches target.

    ``P(q)`` is monotone increasing on ``[0, 0.5]``; a bisection is exact
    enough at float precision and avoids scipy root-finder overhead.
    """
    if target <= 0.0:
        return 0.0
    lo, hi = 0.0, 0.5
    if A.nakamoto_reversal_probability(hi, z, tie_policy) < target:
        return math.inf
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if A.nakamoto_reversal_probability(mid, z, tie_policy) < target:
            lo = mid
        else:
            hi = mid
    return hi


def r6_external_threshold(cfg: dict[str, Any]) -> ExperimentResult:
    """R6 (section 24): external hash required to reach a target probability."""
    res = _result("R6_external_threshold", "II")
    q0 = float(cfg["attacker_shares"]["primary"])
    zs = list(cfg["confirmations"]["default"])
    targets = [0.5, 0.25, 0.10, 0.05, 0.01]
    tables: dict[str, dict[int, float]] = {}
    for target in targets:
        table: dict[int, float] = {}
        for z in zs:
            total_share = _share_for_target(z, target)
            external_share = (
                math.inf if math.isinf(total_share) else max(total_share - q0, 0.0)
            )
            external_hash = (
                math.inf if math.isinf(external_share) else A.external_hash_required(external_share)
            )
            table[z] = external_hash
            rec = ResultRecord(
                experiment="R6_external_threshold", phase="II", model="analytical",
                attacker_share=q0, confirmations=z,
                success_probability=target, code_version=code_version(REPO_ROOT),
            )
            rec.extra["required_total_share"] = total_share
            rec.extra["required_external_share"] = external_share
            rec.extra["required_external_hash_ratio"] = external_hash
            res.records.append(rec)
        tables[f"{target:.2f}"] = table
    res.data = {"q0": q0, "targets": targets, "tables": tables}
    return res


def r7_economics(cfg: dict[str, Any]) -> ExperimentResult:
    """R7 (section 25): economic viability across policies."""
    res = _result("R7_economics", "II")
    q = float(cfg["attacker_shares"]["primary"])
    intervals = [cfg["intervals"]["baseline_sec"], cfg["intervals"]["fast_sec"]]
    zs = list(cfg["confirmations"]["default"])
    rows: list[dict[str, Any]] = []
    for interval in intervals:
        interval = float(interval)
        for z in zs:
            prob = A.nakamoto_reversal_probability(q, z)
            model = EC.attack_value_multiple(
                q, z, prob, expected_attacker_blocks=float(z),
                interval_sec=interval,
            )
            model.double_spend_value = 1_000_000.0
            rec = ResultRecord(
                experiment="R7_economics", phase="II", model="economic",
                target_interval_sec=interval, attacker_share=q, confirmations=z,
                acceptance_policy=_policy_label(interval, z),
                success_probability=prob,
                expected_attack_cost=model.hashing_cost(),
                break_even_value_reward_multiple=model.break_even_multiple(),
                code_version=code_version(REPO_ROOT),
            )
            rec.extra["expected_value"] = model.expected_value()
            rec.extra["break_even_value"] = model.break_even_value()
            res.records.append(rec)
            rows.append(
                {
                    "policy": _policy_label(interval, z),
                    "reversal_probability": prob,
                    "expected_attack_cost": model.hashing_cost(),
                    "break_even_value": model.break_even_value(),
                    "break_even_multiple": model.break_even_multiple(),
                }
            )
    res.data = {"q": q, "rows": rows}
    return res


def r8_cost_accounting(cfg: dict[str, Any]) -> ExperimentResult:
    """R8 (section 26): compare chains on cost, not raw work."""
    res = _result("R8_cost_accounting", "II")
    q = float(cfg["attacker_shares"]["primary"])
    intervals = [cfg["intervals"]["baseline_sec"], cfg["intervals"]["fast_sec"]]
    zs = list(cfg["confirmations"]["default"])
    rows: list[dict[str, Any]] = []
    for interval in intervals:
        interval = float(interval)
        for z in zs:
            prob = A.nakamoto_reversal_probability(q, z)
            baseline = float(cfg["intervals"]["baseline_sec"])
            cost = AT.majority_cost_per_unit_time(q, 1.0, 1.0)
            per_conf = AT.cost_to_reach_confirmations(z, interval, 1.0, 1.0)
            work_cost = AT.cost_of_normalized_work(z, interval, baseline, 1.0, 1.0)
            rec = ResultRecord(
                experiment="R8_cost_accounting", phase="II", model="cost",
                target_interval_sec=interval, attacker_share=q, confirmations=z,
                acceptance_policy=_policy_label(interval, z),
                success_probability=prob,
                expected_attack_cost=work_cost,
                code_version=code_version(REPO_ROOT),
            )
            rec.extra["expected_normalized_work"] = A.normalized_work(z, interval)
            rec.extra["majority_cost_per_unit_time"] = cost
            rec.extra["cost_to_reach_confirmations"] = per_conf
            rec.extra["cost_of_normalized_work"] = work_cost
            res.records.append(rec)
            rows.append(
                {
                    "policy": _policy_label(interval, z),
                    "expected_normalized_work": A.normalized_work(z, interval),
                    "majority_cost_per_unit_time": cost,
                    "cost_to_reach_confirmations": per_conf,
                    "cost_of_normalized_work": work_cost,
                    "reversal_probability": prob,
                }
            )
    res.data = {"q": q, "rows": rows}
    return res


def run_phase2(cfg: dict[str, Any], trials: int | None = None) -> dict[str, ExperimentResult]:
    """Run R1-R8."""
    return {
        "R1": r1_finite_duration(cfg, trials),
        "R2": r2_start_time(cfg, trials),
        "R3": r3_abandonment(cfg, trials),
        "R4": r4_temporary_majority(cfg, trials),
        "R5": r5_acquisition_delay(cfg, trials),
        "R6": r6_external_threshold(cfg),
        "R7": r7_economics(cfg),
        "R8": r8_cost_accounting(cfg),
    }


# --------------------------------------------------------------------------
# Persistence helpers
# --------------------------------------------------------------------------
def collect_records(results: Iterable[ExperimentResult]) -> pd.DataFrame:
    """Concatenate every record from several experiments into one frame."""
    frames = [r.frame() for r in results if r.records]
    if not frames:
        return pd.DataFrame(columns=MASTER_FIELDS)
    # Drop columns that are all-NA within a single experiment so the concat
    # does not mix all-NA and populated dtypes (pandas deprecation).
    frames = [f.dropna(axis=1, how="all") for f in frames]
    return pd.concat(frames, ignore_index=True)


def save_results(
    results: Iterable[ExperimentResult],
    raw_path: str | Path,
    summary_path: str | Path | None = None,
) -> pd.DataFrame:
    """Write the master CSV (and optional summary CSV) for a set of results."""
    frame = collect_records(results)
    raw_path = Path(raw_path)
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(raw_path, index=False)
    if summary_path is not None:
        summary_path = Path(summary_path)
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        keep = [
            c
            for c in (
                "experiment", "phase", "model", "target_interval_sec",
                "attacker_share", "confirmations", "acceptance_policy",
                "success_probability", "ci_lower", "ci_upper",
                "expected_wait_sec", "median_wait_sec", "expected_work",
            )
            if c in frame.columns
        ]
        frame[keep].to_csv(summary_path, index=False)
    return frame


def mvp_frame(cfg: dict[str, Any], trials: int | None = None) -> pd.DataFrame:
    """Section 39 minimum-viable table as a DataFrame."""
    res = mvp_table(cfg, trials)
    return pd.DataFrame(res.data["rows"])


__all__ = [
    "ExperimentResult",
    "load_config",
    "master_seed",
    "p0_analytical_baseline",
    "p1_validate_simulators",
    "p2_policy_comparison",
    "p3_decomposition",
    "p4_interval_comparison",
    "p5_coinbase_claim",
    "p6_equal_chainwork",
    "p7_equal_elapsed_time",
    "p8_frontier",
    "r1_finite_duration",
    "r2_start_time",
    "r3_abandonment",
    "r4_temporary_majority",
    "r5_acquisition_delay",
    "r6_external_threshold",
    "r7_economics",
    "r8_cost_accounting",
    "run_phase1",
    "run_phase2",
    "mvp_table",
    "mvp_frame",
    "collect_records",
    "save_results",
]