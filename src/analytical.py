"""Analytical baseline models (plan section 9 and related).

Conventions
-----------
* ``q`` is the attacker's fraction of total effective hashrate; ``p = 1 - q``.
* Target interval ``T`` seconds; aggregate block rate ``1/T``. Honest rate
  ``p/T``, attacker rate ``q/T``. The next block is the attacker's with
  probability ``q`` independent of ``T`` -- the source of interval
  invariance (plan section 7).
* ``z`` is the merchant-facing confirmation count: ``z = 1`` means the
  transaction is included in the current tip; ``z = 2`` means one block was
  built on top, and so on (plan section 5.3).

Tie policies (plan section 5.4)
-------------------------------
* ``"strict"`` (A): attacker success requires *strictly greater* cumulative
  chainwork, i.e. the race walk must reach ``+1``.
* ``"tie_win"`` (B): equal cumulative chainwork (reaching ``0``) counts as
  success.

For an attacker ``d`` blocks behind, an unbounded gambler's-ruin walk gives

    catch-up("tie_win", d) = (q/p)^d
    catch-up("strict",  d) = (q/p)^(d+1)

Both formulas are derived in the docstrings below.
"""

from __future__ import annotations

import math
from typing import Iterable

import numpy as np
from scipy import special, stats

TIE_POLICIES = ("strict", "tie_win")


# --------------------------------------------------------------------------
# Poisson helpers
# --------------------------------------------------------------------------
def poisson_probs(lam: float, n: int) -> list[float]:
    """P(X = k) for k = 0..n via the stable recurrence.

    ``P(0) = exp(-lam)``, ``P(k+1) = P(k) * lam / (k+1)``. Avoids the
    factorial/e**lam overflow that the naive formula hits for large ``lam``.
    """
    if n < 0:
        return []
    probs = [0.0] * (n + 1)
    probs[0] = math.exp(-lam)
    for k in range(1, n + 1):
        probs[k] = probs[k - 1] * lam / k
    return probs


# --------------------------------------------------------------------------
# Catch-up probability from a known deficit
# --------------------------------------------------------------------------
def catchup_probability(q: float, deficit: int, tie_policy: str = "strict") -> float:
    """Probability the attacker eventually erases ``deficit`` blocks.

    Model: the difference (attacker blocks - honest blocks) is a random walk
    that steps ``+1`` with probability ``q`` and ``-1`` with probability
    ``p = 1 - q``. For ``q < p`` the probability of ever reaching a level
    ``h >= 1`` from level ``-d`` is ``(q/p)^(d + h)``.

    * ``tie_win``  -> ``h = 0`` -> ``(q/p)^deficit``
    * ``strict``   -> ``h = 1`` -> ``(q/p)^(deficit + 1)``

    For ``q >= p`` the walk is recurrent/transient toward success and the
    probability is 1 for any finite deficit.
    """
    if tie_policy not in TIE_POLICIES:
        raise ValueError(f"unknown tie_policy: {tie_policy!r}")
    if deficit < 0:
        raise ValueError("deficit must be non-negative")
    if q <= 0.0:
        return 0.0 if deficit > 0 else 1.0
    if q >= 0.5:
        return 1.0
    ratio = q / (1.0 - q)
    if deficit == 0:
        return 1.0 if tie_policy == "tie_win" else ratio
    return ratio ** (deficit + (1 if tie_policy == "strict" else 0))


# --------------------------------------------------------------------------
# Nakamoto section 11 reversal probability
# --------------------------------------------------------------------------
def _attacker_block_pmf_exact(q: float, z: int, k_max: int) -> np.ndarray:
    """P(K = k) for k = 0..k_max, where K is the attacker's block count at the
    moment the honest chain completes ``z`` confirmations.

    The honest completion time is ``Erlang(z, p/T)``; conditioning on it
    (a Poisson-Gamma mixture) yields the negative binomial

        P(K = k) = C(k + z - 1, k) q^k p^z,   k >= 0.
    """
    p = 1.0 - q
    ks = np.arange(k_max + 1)
    log_coef = special.gammaln(ks + z) - special.gammaln(ks + 1) - special.gammaln(z)
    log_pmf = log_coef + ks * math.log(q) + z * math.log(p) if q > 0 else np.full_like(
        ks, -np.inf, dtype=float
    )
    return np.exp(log_pmf)


def nakamoto_reversal_probability(
    q: float, z: int, tie_policy: str = "tie_win"
) -> float:
    """Eventual reversal probability after ``z`` confirmations.

    Exact finite-horizon model: honest completes ``z`` confirmations; the
    attacker's block count ``K`` at that instant is negative binomial (see
    :func:`_attacker_block_pmf_exact`). From a deficit ``d = z - K`` the
    attacker catches up with :func:`catchup_probability`. If already at or
    beyond the success boundary, the probability is 1.

        P(reverse) = sum_k P(K=k) * catch-up(max(z - k, 0))
                     + P(K beyond the success boundary)

    This is the "exact / negative-binomial" model. For the whitepaper's
    Poisson *approximation* (which replaces the Erlang completion time by its
    mean), see :func:`nakamoto_reversal_probability_poisson`.
    """
    if tie_policy not in TIE_POLICIES:
        raise ValueError(f"unknown tie_policy: {tie_policy!r}")
    if z < 1:
        raise ValueError("z must be >= 1")
    if q >= 0.5:
        return 1.0
    if q <= 0.0:
        return 0.0

    p = 1.0 - q
    ratio = q / p
    # Success boundary in attacker block count.
    boundary = z + (1 if tie_policy == "strict" else 0)
    k_max = boundary
    pmf = _attacker_block_pmf_exact(q, z, k_max)
    total = 0.0
    for k in range(0, boundary):
        d = z - k  # deficit (>=0)
        total += pmf[k] * catchup_probability(q, d, tie_policy)
    # k >= boundary: already successful.
    tail = 1.0 - pmf[:boundary].sum()
    total += tail
    return float(min(1.0, max(0.0, total)))


def nakamoto_reversal_probability_poisson(
    q: float, z: int, tie_policy: str = "tie_win"
) -> float:
    """Whitepaper-style Poisson approximation of the reversal probability.

    Nakamoto models the attacker's block count during the honest ``z``
    confirmation period as ``Poisson(lambda)`` with ``lambda = z * q / p``
    (the mean of the exact distribution), then

        P(fail) = sum_{k=0}^{z} Pois(lambda, k) * (1 - catch-up(z - k)).

    ``k > z`` is treated as an immediate success.
    """
    if tie_policy not in TIE_POLICIES:
        raise ValueError(f"unknown tie_policy: {tie_policy!r}")
    if z < 1:
        raise ValueError("z must be >= 1")
    if q >= 0.5:
        return 1.0
    if q <= 0.0:
        return 0.0
    lam = z * q / (1.0 - q)
    pmf = poisson_probs(lam, z)
    fail = 0.0
    for k in range(0, z + 1):
        d = z - k
        fail += pmf[k] * (1.0 - catchup_probability(q, d, tie_policy))
    return float(min(1.0, max(0.0, 1.0 - fail)))


# --------------------------------------------------------------------------
# General two-process race: I_q(a, b)
# --------------------------------------------------------------------------
def race_probability(q: float, a: int, b: int) -> float:
    """P(attacker reaches ``a`` blocks before honest reaches ``b``) = I_q(a, b).

    ``I_q`` is the regularized incomplete beta function. With no head start
    and independent Poisson streams, the sequence of block originators is
    i.i.d. Bernoulli(q), so the probability the ``a``-th attacker block
    precedes the ``b``-th honest block is ``I_q(a, b)``.

    Used for:
    * Fablous double-spend ``P(overtake) = I_q(m, m)``;
    * sniping ``P(overtake) = I_q(n + m, m)``.
    """
    if a < 1 or b < 1:
        raise ValueError("a and b must be >= 1")
    if q <= 0.0:
        return 0.0
    if q >= 1.0:
        return 1.0
    return float(special.betainc(a, b, q))


# --------------------------------------------------------------------------
# Deficit distribution at acceptance (for decomposition, plan section 12)
# --------------------------------------------------------------------------
def attacker_deficit_distribution(q: float, z: int) -> dict[int, float]:
    """P(deficit = d) at merchant acceptance, ``d`` blocks behind (d>=0),
    plus ``d = -1`` aggregating the attacker being strictly ahead.

    Exact negative-binomial mass at the instant honest completes ``z``
    confirmations. ``d = z - k``; the mass at ``d = -1`` collects all
    ``k > z``.
    """
    if z < 1:
        raise ValueError("z must be >= 1")
    p = 1.0 - q
    dist: dict[int, float] = {}
    for k in range(0, z + 1):
        # scipy nbinom "p" is the probability of the *honest* block (1 - q).
        dist[z - k] = (
            float(stats.nbinom.pmf(k, z, p)) if q > 0 else (1.0 if k == 0 else 0.0)
        )
    dist[-1] = float(stats.nbinom.sf(z, z, p)) if q > 0 else 0.0
    return dist


def reversal_decomposition(
    q: float, z: int, tie_policy: str = "tie_win"
) -> list[tuple[int, float, float, float]]:
    """Return ``(deficit, P(D=d), catchup, contribution)`` rows.

    ``contribution = P(D=d) * catchup``; the sum equals
    :func:`nakamoto_reversal_probability` (modulo the ahead-mass, whose
    catch-up is 1).
    """
    dist = attacker_deficit_distribution(q, z)
    rows: list[tuple[int, float, float, float]] = []
    for d, prob in sorted(dist.items(), reverse=True):
        if d == -1:
            cu = 1.0
        else:
            cu = catchup_probability(q, d, tie_policy)
        rows.append((d, prob, cu, prob * cu))
    return rows


# --------------------------------------------------------------------------
# Tick-scaled parking schedule (Fablous / Stone)
# --------------------------------------------------------------------------
def lag_allowed_ticks(m: int, ticks_per_block: int) -> float:
    """Max lag (in blocks) a fork may have before its nodes flip away.

    Keyed on main-chain depth ``m`` and expressed in ticks. Tick bands:
    ``< 600`` -> 0.5 blocks; ``600-1799`` -> 300/ticks_per_block;
    ``1800-2399`` -> 600/ticks_per_block; ``>= 2400`` -> m/2 (2x work).
    """
    tick_depth = m * ticks_per_block
    if tick_depth < 600:
        return 0.5
    if tick_depth < 1800:
        return 300.0 / ticks_per_block
    if tick_depth < 2400:
        return 600.0 / ticks_per_block
    return m / 2.0


def penalty_blocks(m: int, ticks_per_block: int) -> int:
    """Minimum fork length ``f`` needed to overtake a defending tip at
    main-chain depth ``m`` (strict: ``f > m + extra``)."""
    tick_depth = m * ticks_per_block
    if tick_depth < 600:
        extra = 0.5
    elif tick_depth < 1800:
        extra = 300.0 / ticks_per_block
    elif tick_depth < 2400:
        extra = 600.0 / ticks_per_block
    else:
        extra = float(m)
    return math.floor(m + extra) + 1


# --------------------------------------------------------------------------
# Economic helper: break-even value / reward ratio
# --------------------------------------------------------------------------
def doublespend_break_even_multiple(q: float, m: int) -> float:
    """``X / C = (m - 1) / P`` with ``P = I_q(m, m)`` (Fablous convention).

    ``m - 1`` is the recipient's confirmation requirement; ``X`` is the
    double-spend value, ``C`` the coinbase. Returns ``inf`` when ``P = 0``.
    """
    p = race_probability(q, m, m)
    if p <= 0.0:
        return math.inf
    return (m - 1) / p


def sniping_break_even_multiple(q: float, n: int, m: int) -> float:
    """``X / C = (n + m) * (1 / P - 1)`` with ``P = I_q(n + m, m)``."""
    p = race_probability(q, n + m, m)
    if p <= 0.0:
        return math.inf
    return (n + m) * (1.0 / p - 1.0)


def external_hash_required(q: float, honest_hashrate: float = 1.0) -> float:
    """External attacker hashrate ``A`` needed for share ``q``: A = q/(1-q) * H."""
    if not (0.0 <= q < 1.0):
        raise ValueError("q must be in [0, 1)")
    return q / (1.0 - q) * honest_hashrate


# --------------------------------------------------------------------------
# Waiting-time helpers
# --------------------------------------------------------------------------
def expected_wait_sec(z: int, interval_sec: float) -> float:
    """Nominal expected wait for ``z`` confirmations: ``z * T``."""
    return z * interval_sec


def wait_time_quantiles(
    z: int, interval_sec: float, quantiles: Iterable[float] = (0.5,)
) -> list[float]:
    """Quantiles of the wait until ``z`` blocks arrive, at nominal cadence.

    Blocks arrive as a Poisson process with rate ``1/T``; the waiting time
    to the ``z``-th block is ``Erlang(z, 1/T)`` (``Gamma(z, scale=T)``).
    """
    qs = list(quantiles)
    return [float(stats.gamma.ppf(qq, a=z, scale=interval_sec)) for qq in qs]


def median_wait_sec(z: int, interval_sec: float) -> float:
    return wait_time_quantiles(z, interval_sec, (0.5,))[0]


def normalized_work(
    z: int, interval_sec: float, baseline_interval_sec: float = 600.0
) -> float:
    """Expected normalized chainwork for ``z`` confirmations.

    With ``W_600 = 1.0`` and unchanged total hashrate, ``W_60 = 0.1``; work
    per block scales as ``T / baseline`` (plan section 5.1-5.2).
    """
    return z * (interval_sec / baseline_interval_sec)