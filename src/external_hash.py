"""Temporary / externally acquired SHA-256 hashpower (plan sections 22-24).

R4-R6 relax the assumption that the attacker's share is stationary:

* R4 temporary majority   -- share jumps to ``q_active`` for a window.
* R5 delayed acquisition   -- the jump begins after ``acquisition_delay`` sec.
* R6 external threshold    -- how much *external* hashrate is needed for a
  target share: ``A = q / (1 - q) * H`` (the honest network ``H`` stays fixed,
  so acquiring share ``q`` dilutes the honest share).

The simulation advances in wall-clock time: each block arrives after an
``Exp(1/T)`` delay and its owner is Bernoulli with the share *at that instant*,
so a temporary surge is honoured exactly in wall-clock terms. The merchant
accepts once the honest chain reaches ``z`` confirmations; only thereafter can
the attacker "win", but a secret chain built during the surge is retained.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from .analytical import external_hash_required
from .mining import ReversalSimResult, _success_boundary
from .statistics import derive_seed, make_rng, wilson_interval


@dataclass
class ExternalHashResult(ReversalSimResult):
    """Reversal result for a time-varying (external) hashpower schedule."""

    q0: float = 0.0
    q_active: float = 0.0
    acquisition_delay_sec: float = 0.0
    active_duration_sec: float = 0.0
    deadline_sec: float | None = None
    interval_sec: float = 600.0
    extra: dict[str, Any] = field(default_factory=dict)


def _share_schedule(
    t: np.ndarray, q0: float, q_active: float, activation: float, duration: float
) -> np.ndarray:
    """Total attacker share as a function of wall-clock time."""
    if duration <= 0.0:
        return np.full_like(t, q0, dtype=float)
    active = (t >= activation) & (t < activation + duration)
    return np.where(active, q_active, q0)


def temporary_hash_reversal(
    q0: float,
    q_active: float,
    acquisition_delay_sec: float,
    active_duration_sec: float,
    z: int,
    deadline_sec: float,
    interval_sec: float = 600.0,
    tie_policy: str = "tie_win",
    trials: int = 100_000,
    master_seed: int = 20250924,
    seed_label: Any = "external_hash",
    failure_lag: int = 250,
    max_blocks: int = 5_000_000,
) -> ExternalHashResult:
    """Reversal probability with a temporary share surge.

    The attacker holds share ``q0``, jumps to ``q_active`` at
    ``acquisition_delay_sec`` for ``active_duration_sec``, then reverts to
    ``q0``. The attack is bounded by ``deadline_sec``.
    """
    if z < 1:
        raise ValueError("z must be >= 1")
    for name, val in (("q0", q0), ("q_active", q_active)):
        if not (0.0 <= val <= 1.0):
            raise ValueError(f"{name} must be in [0, 1]")

    boundary = _success_boundary(tie_policy)
    rng = make_rng(master_seed, seed_label, q0, q_active, acquisition_delay_sec,
                   active_duration_sec, z, deadline_sec, interval_sec, tie_policy, trials)

    t = np.zeros(trials, dtype=np.float64)
    s = np.zeros(trials, dtype=np.int64)
    honest = np.zeros(trials, dtype=np.int64)
    attacker = np.zeros(trials, dtype=np.int64)
    released = np.zeros(trials, dtype=bool)
    success = np.zeros(trials, dtype=bool)
    done = np.zeros(trials, dtype=bool)
    deficit = np.zeros(trials, dtype=np.int64)
    release_time = np.zeros(trials, dtype=np.float64)

    for _ in range(max_blocks):
        idx = np.flatnonzero(~done)
        if idx.size == 0:
            break
        dt = rng.exponential(interval_sec, size=idx.size)
        t[idx] += dt
        q_now = _share_schedule(t[idx], q0, q_active,
                                float(acquisition_delay_sec), float(active_duration_sec))
        attacker_wins = rng.random(idx.size) < q_now
        honest[idx] += ~attacker_wins
        attacker[idx] += attacker_wins
        s[idx] += np.where(attacker_wins, 1, -1)

        just = idx[(~released[idx]) & (honest[idx] >= z)]
        if just.size:
            released[just] = True
            deficit[just] = -s[just]
            release_time[just] = t[just]

        rel = idx[released[idx]]
        if rel.size:
            won = rel[s[rel] >= boundary]
            success[won] = True
            done[won] = True
            lost = rel[(s[rel] <= -failure_lag) | (t[rel] > deadline_sec)]
            done[lost] = True
        # Never keep a trial alive past its deadline.
        over = idx[(~done[idx]) & (t[idx] > deadline_sec)]
        done[over] = True

    successes = int(success.sum())
    lo, hi = wilson_interval(successes, trials)
    return ExternalHashResult(
        trials=trials,
        successes=successes,
        q=q_active,
        z=z,
        tie_policy=tie_policy,
        p_hat=successes / trials,
        ci_lower=lo,
        ci_upper=hi,
        mean_deficit_at_acceptance=float(deficit.mean()),
        mean_acceptance_blocks=float(honest[released].mean()) if released.any() else 0.0,
        mean_attacker_blocks_at_acceptance=float(attacker[released].mean()) if released.any() else 0.0,
        unresolved=0,
        seed=derive_seed(master_seed, seed_label, q0, q_active, acquisition_delay_sec,
                         active_duration_sec, z, deadline_sec, interval_sec, tie_policy, trials),
        q0=q0,
        q_active=q_active,
        acquisition_delay_sec=acquisition_delay_sec,
        active_duration_sec=active_duration_sec,
        deadline_sec=deadline_sec,
        interval_sec=interval_sec,
        extra={"mean_release_time_sec": float(release_time.mean())},
    )


def temporary_majority_grid(
    q0: float,
    shares: list[float],
    durations_sec: list[float],
    z: int,
    deadline_sec: float,
    interval_sec: float = 600.0,
    trials: int = 20_000,
    master_seed: int = 20250924,
) -> dict[tuple[float, float], ExternalHashResult]:
    """R4 heatmap grid over (active share, duration)."""
    out: dict[tuple[float, float], ExternalHashResult] = {}
    for share in shares:
        for duration in durations_sec:
            out[(share, duration)] = temporary_hash_reversal(
                q0=q0,
                q_active=share,
                acquisition_delay_sec=0.0,
                active_duration_sec=duration,
                z=z,
                deadline_sec=deadline_sec,
                interval_sec=interval_sec,
                trials=trials,
                master_seed=master_seed,
                seed_label="r4",
            )
    return out


def acquisition_delay_grid(
    q0: float,
    shares: list[float],
    delays_sec: list[float],
    active_duration_sec: float,
    z: int,
    deadline_sec: float,
    interval_sec: float = 600.0,
    trials: int = 20_000,
    master_seed: int = 20250924,
) -> dict[tuple[float, float], ExternalHashResult]:
    """R5 heatmap grid over (acquisition delay, active share)."""
    out: dict[tuple[float, float], ExternalHashResult] = {}
    for delay in delays_sec:
        for share in shares:
            out[(delay, share)] = temporary_hash_reversal(
                q0=q0,
                q_active=share,
                acquisition_delay_sec=delay,
                active_duration_sec=active_duration_sec,
                z=z,
                deadline_sec=deadline_sec,
                interval_sec=interval_sec,
                trials=trials,
                master_seed=master_seed,
                seed_label="r5",
            )
    return out


__all__ = [
    "ExternalHashResult",
    "temporary_hash_reversal",
    "temporary_majority_grid",
    "acquisition_delay_grid",
    "external_hash_required",
    "_share_schedule",
]
