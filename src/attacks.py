"""Robustness experiments R1-R3 and R8 (plan sections 19-22, 26).

These relax the idealized "attacker mines in secret from time zero, unlimited
time" assumptions of the core model:

* R1 finite duration       -> :func:`finite_horizon_reversal`
* R2 start-time sensitivity -> ``start_policy`` / ``premining_lead``
* R3 rational abandonment   -> ``abandonment_deficit``
* R8 cost accounting        -> :func:`majority_cost_per_unit_time` etc.

The horizon model
-----------------
Blocks in a wall-clock window of length ``H`` arrive as a Poisson process of
rate ``1/T``; each is the attacker's with probability ``q`` independent of
``T``. Conditional on the window we therefore only need the *number* of
blocks, which is ``Poisson(H / T)``. That keeps the model exact in wall-clock
terms while preserving interval invariance in the unit of blocks.

The race state is ``s = attacker_blocks - honest_blocks``. Success is
``s >= boundary`` (0 for ``tie_win``, 1 for ``strict``). Acceptance occurs when
the honest chain reaches ``z`` confirmations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from .mining import ReversalSimResult, _success_boundary
from .statistics import derive_seed, make_rng, wilson_interval

START_POLICIES = ("simultaneous", "at_inclusion", "reactive", "premining")


@dataclass
class HorizonResult(ReversalSimResult):
    """A :class:`ReversalSimResult` carrying robustness metadata."""

    deadline_sec: float | None = None
    start_policy: str = "simultaneous"
    start_delay_sec: float = 0.0
    premining_lead: int = 0
    abandonment_deficit: int | None = None
    interval_sec: float = 600.0
    extra: dict[str, Any] = field(default_factory=dict)


def finite_horizon_reversal(
    q: float,
    z: int,
    deadline_sec: float,
    interval_sec: float = 600.0,
    tie_policy: str = "tie_win",
    start_policy: str = "simultaneous",
    start_delay_sec: float = 0.0,
    premining_lead: int = 0,
    abandonment_deficit: int | None = None,
    trials: int = 200_000,
    master_seed: int = 20250924,
    seed_label: Any = "finite_horizon",
    failure_lag_cap: int = 250,
) -> HorizonResult:
    """Probability the attacker reverses within ``deadline_sec`` seconds.

    Parameters
    ----------
    deadline_sec:
        Wall-clock budget measured from transaction inclusion.
    start_policy:
        * ``"simultaneous"`` / ``"at_inclusion"`` -- attacker mines from the
          outset (core model): acceptance time ``Gamma(z, T/p)``.
        * ``"reactive"`` -- attacker only switches on ``start_delay_sec`` after
          inclusion; honest mines alone until then, so acceptance is delayed
          and the attacker earns no early blocks (approximation).
        * ``"premining"`` -- attacker has ``premining_lead`` secret blocks
          before the transaction is broadcast, reducing the catch-up deficit.
    abandonment_deficit:
        R3: attacker gives up once ``abandonment_deficit`` blocks behind.
        ``None`` uses the large ``failure_lag_cap`` (effectively never).
    """
    if z < 1:
        raise ValueError("z must be >= 1")
    if not (0.0 <= q <= 1.0):
        raise ValueError("q must be in [0, 1]")
    if start_policy not in START_POLICIES:
        raise ValueError(f"unknown start_policy: {start_policy!r}")

    boundary = _success_boundary(tie_policy)
    failure_lag = failure_lag_cap if abandonment_deficit is None else int(abandonment_deficit)
    if failure_lag < 1:
        raise ValueError("abandonment_deficit must be >= 1")
    p = 1.0 - q
    rng = make_rng(master_seed, seed_label, q, z, tie_policy, deadline_sec,
                   start_policy, start_delay_sec, premining_lead, abandonment_deficit, trials)

    def _result(successes: int, deficit0: float, ka: float, extra: dict[str, Any]) -> HorizonResult:
        lo, hi = wilson_interval(successes, trials)
        return HorizonResult(
            trials=trials,
            successes=successes,
            q=q,
            z=z,
            tie_policy=tie_policy,
            p_hat=successes / trials,
            ci_lower=lo,
            ci_upper=hi,
            mean_deficit_at_acceptance=deficit0,
            mean_acceptance_blocks=float(z),
            mean_attacker_blocks_at_acceptance=ka,
            unresolved=0,
            seed=derive_seed(master_seed, seed_label, q, z, tie_policy, deadline_sec,
                             start_policy, start_delay_sec, premining_lead, abandonment_deficit, trials),
            deadline_sec=deadline_sec,
            start_policy=start_policy,
            start_delay_sec=start_delay_sec,
            premining_lead=premining_lead,
            abandonment_deficit=abandonment_deficit,
            interval_sec=interval_sec,
            extra=extra,
        )

    if q <= 0.0:
        return _result(0, float(z), 0.0, {})

    # ---- acceptance time and attacker blocks at acceptance -----------------
    if start_policy == "reactive":
        delay = float(start_delay_sec)
        # Honest mines alone for `delay`, then both streams run. Acceptance is
        # approximated as delay + Gamma(z, T) (honest completion at full rate).
        t_accept = delay + rng.gamma(shape=z, scale=interval_sec, size=trials)
        active_window = np.maximum(t_accept - delay, 0.0)
        k = rng.poisson((q / interval_sec) * active_window)
    else:
        t_accept = rng.gamma(shape=z, scale=interval_sec / p, size=trials)
        k = rng.poisson((q / interval_sec) * t_accept)

    lead = int(premining_lead) if start_policy == "premining" else 0
    deficit = np.maximum(z - lead - k, 0)
    # Parity-success when the secret chain already matches the public one.
    success = (lead + k) >= (z + boundary)
    success &= t_accept <= deadline_sec

    allowed_steps = np.floor(
        np.maximum(deadline_sec - t_accept, 0.0) * (1.0 / interval_sec)
    ).astype(np.int64)

    s = -deficit.astype(np.int64)
    steps_taken = np.zeros(trials, dtype=np.int64)
    active = np.flatnonzero(~success)
    while active.size:
        active = active[steps_taken[active] < allowed_steps[active]]
        if active.size == 0:
            break
        draw = rng.random(active.size)
        s[active] += np.where(draw < q, 1, -1)
        steps_taken[active] += 1
        won = active[s[active] >= boundary]
        success[won] = True
        active = active[(s[active] < boundary) & (s[active] > -failure_lag)]

    return _result(
        int(success.sum()),
        float(deficit.mean()),
        float(k.mean()),
        {"mean_steps_taken": float(steps_taken.mean()), "failure_lag": failure_lag},
    )


# --------------------------------------------------------------------------
# R8 -- cost accounting across intervals (plan section 26)
# --------------------------------------------------------------------------
def majority_cost_per_unit_time(
    attacker_share: float, total_hashrate: float, cost_per_hash_sec: float
) -> float:
    """Attacker cost per wall-clock second at a fixed hash share.

    Independent of target interval, so a faster interval does not hand the
    attacker a cost advantage -- it must sustain the same hashrate for the
    same wall-clock duration (claim C4).
    """
    return attacker_share * total_hashrate * cost_per_hash_sec


def cost_to_reach_confirmations(
    confirmations: int,
    interval_sec: float,
    total_hashrate: float,
    cost_per_hash_sec: float,
) -> float:
    """Cost to *reach* ``confirmations`` at nominal cadence (wall-clock bound)."""
    return confirmations * interval_sec * total_hashrate * cost_per_hash_sec


def cost_of_normalized_work(
    confirmations: int,
    interval_sec: float,
    baseline_interval_sec: float,
    total_hashrate: float,
    cost_per_hash_sec: float,
) -> float:
    """Cost of the *chainwork* accumulated by ``confirmations``.

    Equal chainwork costs the attacker equally regardless of interval; this
    is the quantity that must not be conflated with wall-clock cost.
    """
    normalized = confirmations * interval_sec / baseline_interval_sec
    return normalized * baseline_interval_sec * total_hashrate * cost_per_hash_sec
