"""Two independent Monte Carlo simulators (plan section 32).

Design intent
-------------
The plan requires two *independent* implementations so that agreement is
meaningful and neither silently inherits a bug from the other:

* :func:`simulate_reversal_bernoulli` -- discrete event-driven block
  sequence. Each block's originator is a fresh Bernoulli(q) draw; no closed
  form is used anywhere. Most assumption-free, used at dev scale.
* :func:`simulate_reversal_distribution` -- distribution-based. The honest
  completion time is Gamma and the attacker's block count conditional on it
  is Poisson (equivalently negative binomial at the mean); the remaining race
  is resolved by a vectorized walk. Used at final scale.

Both resolve the *unbounded* race until the walk reaches the success
boundary or falls ``failure_lag`` blocks behind. The finite ``failure_lag``
is an explicit, documented approximation to infinity; it biases reversal
estimates downward by an amount that vanishes as ``failure_lag`` grows (the
error is ``~ (q/p)^(failure_lag)``).

State is ``s = attacker_blocks - honest_blocks``.

* ``tie_win``  -> success boundary ``s >= 0``.
* ``strict``   -> success boundary ``s >= 1``.

Merchant acceptance occurs when the honest chain reaches ``z`` blocks; the
secret chain is only *compared* at that instant. Because the attacker count
at acceptance is at most the honest count ``z``, the post-acceptance deficit
is ``<= z`` -- small -- which keeps the walk cheap.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from .statistics import derive_seed, make_rng, wilson_interval


@dataclass
class ReversalSimResult:
    """Outcome of a reversal simulation."""

    trials: int
    successes: int
    q: float
    z: int
    tie_policy: str
    p_hat: float
    ci_lower: float
    ci_upper: float
    mean_deficit_at_acceptance: float
    mean_acceptance_blocks: float
    mean_attacker_blocks_at_acceptance: float
    unresolved: int
    seed: int
    extra: dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:  # pragma: no cover - cosmetic
        return (
            f"ReversalSim(q={self.q}, z={self.z}, {self.tie_policy}): "
            f"p={self.p_hat:.6f} [{self.ci_lower:.6f}, {self.ci_upper:.6f}] "
            f"(n={self.trials})"
        )


def _success_boundary(tie_policy: str) -> int:
    if tie_policy == "tie_win":
        return 0
    if tie_policy == "strict":
        return 1
    raise ValueError(f"unknown tie_policy: {tie_policy!r}")


# --------------------------------------------------------------------------
# Simulator A: discrete Bernoulli block sequence (reference)
# --------------------------------------------------------------------------
def simulate_reversal_bernoulli(
    q: float,
    z: int,
    tie_policy: str = "tie_win",
    trials: int = 100_000,
    master_seed: int = 20250924,
    seed_label: Any = "bernoulli",
    failure_lag: int = 250,
    max_steps: int = 2_000_000,
) -> ReversalSimResult:
    """Discrete event-driven simulation of the eventual reversal race.

    Trials advance in lock-step, vectorized over the active set. Each step
    samples one block owner per active trial (Bernoulli(q)). This is
    equivalent to sampling exponential inter-arrival times and taking the
    faster stream, without per-event Python overhead.
    """
    if z < 1:
        raise ValueError("z must be >= 1")
    if not (0.0 <= q <= 1.0):
        raise ValueError("q must be in [0, 1]")

    rng = make_rng(master_seed, seed_label, q, z, tie_policy, trials)
    boundary = _success_boundary(tie_policy)

    s = np.zeros(trials, dtype=np.int64)
    honest = np.zeros(trials, dtype=np.int64)
    attacker = np.zeros(trials, dtype=np.int64)
    released = np.zeros(trials, dtype=bool)
    success = np.zeros(trials, dtype=bool)
    done = np.zeros(trials, dtype=bool)
    deficit = np.zeros(trials, dtype=np.int64)
    accept_blocks = np.zeros(trials, dtype=np.int64)
    attacker_at_accept = np.zeros(trials, dtype=np.int64)

    if q >= 0.5:
        # A majority attacker succeeds eventually regardless of timing.
        success[:] = True
        done[:] = True
        released[:] = True
        honest[:] = z
        accept_blocks[:] = z

    for _ in range(max_steps):
        idx = np.flatnonzero(~done)
        if idx.size == 0:
            break
        draw = rng.random(idx.size)
        attacker_wins = draw < q
        # The public chain is extended only by honest blocks; attacker blocks
        # are withheld (secret). s tracks attacker - honest.
        honest[idx] += ~attacker_wins
        s[idx] += np.where(attacker_wins, 1, -1)
        attacker[idx] += attacker_wins

        just_released = idx[(~released[idx]) & (honest[idx] >= z)]
        if just_released.size:
            released[just_released] = True
            deficit[just_released] = -s[just_released]
            accept_blocks[just_released] = honest[just_released]
            attacker_at_accept[just_released] = attacker[just_released]

        rel = idx[released[idx]]
        if rel.size:
            won = rel[s[rel] >= boundary]
            success[won] = True
            done[won] = True
            lost = rel[s[rel] <= -failure_lag]
            done[lost] = True

    unresolved = int((~done).sum())
    successes = int(success.sum())
    lo, hi = wilson_interval(successes, trials)
    return ReversalSimResult(
        trials=trials,
        successes=successes,
        q=q,
        z=z,
        tie_policy=tie_policy,
        p_hat=successes / trials,
        ci_lower=lo,
        ci_upper=hi,
        mean_deficit_at_acceptance=float(deficit.mean()),
        mean_acceptance_blocks=float(accept_blocks.mean()),
        mean_attacker_blocks_at_acceptance=float(attacker_at_accept.mean()),
        unresolved=unresolved,
        seed=derive_seed(master_seed, seed_label, q, z, tie_policy, trials),
    )


# --------------------------------------------------------------------------
# Simulator B: distribution-based (Gamma + Poisson)
# --------------------------------------------------------------------------
def simulate_reversal_distribution(
    q: float,
    z: int,
    tie_policy: str = "tie_win",
    interval_sec: float = 600.0,
    trials: int = 1_000_000,
    master_seed: int = 20250924,
    seed_label: Any = "distribution",
    failure_lag: int = 250,
    deadline_sec: float | None = None,
) -> ReversalSimResult:
    """Distribution-based simulation.

    1. Honest completion time ``t ~ Gamma(z, scale=T/p)``.
    2. Attacker count during ``t``: ``K ~ Poisson((q/T) * t)``.
    3. Immediate success when ``K`` is at or beyond the success boundary;
       otherwise deficit ``d = max(z - K, 0)``.
    4. Remaining catch-up race resolved by a vectorized walk over ``d``.

    The ``q >= 0.5`` case is trivially certain (unlimited time).

    With ``deadline_sec`` set, the attack is finite-horizon: acceptance must
    occur before the deadline and the catch-up walk is capped at the number
    of blocks that can still arrive before it. Unresolved trials count as
    failures, so the finite-horizon estimate is always <= the unlimited one.
    """
    if z < 1:
        raise ValueError("z must be >= 1")
    if not (0.0 <= q <= 1.0):
        raise ValueError("q must be in [0, 1]")

    rng = make_rng(master_seed, seed_label, q, z, tie_policy, trials)
    boundary = _success_boundary(tie_policy)
    p = 1.0 - q

    if q <= 0.0:
        lo, hi = wilson_interval(0, trials)
        return ReversalSimResult(
            trials=trials, successes=0, q=q, z=z, tie_policy=tie_policy,
            p_hat=0.0, ci_lower=lo, ci_upper=hi,
            mean_deficit_at_acceptance=float(z),
            mean_acceptance_blocks=float(z),
            mean_attacker_blocks_at_acceptance=0.0,
            unresolved=0,
            seed=derive_seed(master_seed, seed_label, q, z, tie_policy, trials),
        )

    if q >= 0.5:
        lo, hi = wilson_interval(trials, trials)
        return ReversalSimResult(
            trials=trials, successes=trials, q=q, z=z, tie_policy=tie_policy,
            p_hat=1.0, ci_lower=lo, ci_upper=hi,
            mean_deficit_at_acceptance=0.0,
            mean_acceptance_blocks=float(z),
            mean_attacker_blocks_at_acceptance=float(q * z / p),
            unresolved=0,
            seed=derive_seed(master_seed, seed_label, q, z, tie_policy, trials),
        )

    t_accept = rng.gamma(shape=z, scale=interval_sec / p, size=trials)
    k = rng.poisson((q / interval_sec) * t_accept)

    deficit = np.maximum(z - k, 0)
    success = k >= (z + boundary)
    deficit_at_accept = deficit.astype(np.float64)

    if deadline_sec is not None:
        # Acceptance after the deadline is an automatic failure.
        success &= t_accept <= deadline_sec
        # Each walk step corresponds to one block (total rate 1/T); the
        # number of remaining steps before the deadline is bounded.
        allowed_steps = np.floor((deadline_sec - t_accept) * (1.0 / interval_sec))
        allowed_steps = np.maximum(allowed_steps, 0.0).astype(np.int64)
    else:
        allowed_steps = np.full(trials, np.iinfo(np.int64).max, dtype=np.int64)

    s = -deficit.astype(np.int64)
    steps_taken = np.zeros(trials, dtype=np.int64)
    active = np.flatnonzero(~success)
    while active.size:
        # Drop trials that have exhausted their finite-horizon step budget.
        active = active[steps_taken[active] < allowed_steps[active]]
        if active.size == 0:
            break
        draw = rng.random(active.size)
        s[active] += np.where(draw < q, 1, -1)
        steps_taken[active] += 1
        won = active[s[active] >= boundary]
        success[won] = True
        active = active[(s[active] < boundary) & (s[active] > -failure_lag)]

    successes = int(success.sum())
    lo, hi = wilson_interval(successes, trials)
    return ReversalSimResult(
        trials=trials,
        successes=successes,
        q=q,
        z=z,
        tie_policy=tie_policy,
        p_hat=successes / trials,
        ci_lower=lo,
        ci_upper=hi,
        mean_deficit_at_acceptance=float(deficit_at_accept.mean()),
        mean_acceptance_blocks=float(z),
        mean_attacker_blocks_at_acceptance=float(k.mean()),
        unresolved=0,
        seed=derive_seed(master_seed, seed_label, q, z, tie_policy, trials),
    )