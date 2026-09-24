"""Faithful port of Fablous ``extras/stone/stone_all_attacks.py``.

This module reproduces the proponent's own attack models *exactly* so that
their published tables and curves can be used as a regression oracle before
any extension. Do not "improve" the formulas here; extensions live in
``attacks.py`` / ``external_hash.py``.

Source: gitlab.com/0353F40E/fablous, ``extras/stone/stone_all_attacks.py``.
"""

from __future__ import annotations

import math

import numpy as np

from .analytical import lag_allowed_ticks, penalty_blocks, poisson_probs

__all__ = [
    "poisson_probs",
    "lag_allowed_ticks",
    "penalty_blocks",
    "fin_park_fork_two_sided",
    "dspart",
    "doublespend_attack",
    "doublespend_attack_tie",
    "limited_double_spend_attack_iter",
    "fork_matching_curve",
    "double_spend_curve",
]

# Reference configuration used by the proponent's __main__.
BCH_FIN = 10
BCH_TPB = 600
NEW_FIN = 100
NEW_TPB = 60
EMBARGO_CONFIGS = [(1, 1), (1, 10), (10, 100)]


# --------------------------------------------------------------------------
# Fork-matching / parking DP
# --------------------------------------------------------------------------
def fin_park_fork_two_sided(
    attacker_hash: float,
    finalization_depth: int,
    parking: bool = True,
    ticks_per_block: int = 60,
) -> float:
    """Probability an attacker fork overtakes a finalizing tip.

    Direct port of ``FinParkFork_TwoSided``. ``W[m][f]`` is the success
    probability from main-chain depth ``m`` and fork length ``f``; the state
    is absorbed once ``f >= finalization_depth`` (fork wins) or the fork has
    fallen more than ``lag_allowed_ticks`` behind.
    """
    q = attacker_hash
    p = 1.0 - q
    interval = q / p

    max_m = 3 * finalization_depth + 5
    probs = poisson_probs(interval, finalization_depth + 5)
    probs_above = [0.0] * len(probs)
    for i in range(len(probs)):
        probs_above[i] = 1.0 - sum(probs[:i])

    w = [[0.0] * (finalization_depth + 1) for _ in range(max_m)]

    for f in range(finalization_depth, -1, -1):
        if f >= finalization_depth:
            for m in range(max_m):
                w[m][f] = 1.0
            continue
        for m in range(max_m - 1, -1, -1):
            if m + 1 >= max_m:
                w[m][f] = 0.0
            elif m == 0:
                # Fork is free to start at depth 0; falls through to acc.
                lag = lag_allowed_ticks(m, ticks_per_block) if parking else 0.0
                if f < m - lag:
                    w[m][f] = 0.0
                    continue
                acc = 0.0
                for i in range(0, finalization_depth - f):
                    acc += probs[i] * w[m + 1][f + i]
                acc += probs_above[finalization_depth - f]
                w[m][f] = acc
            else:
                lag = lag_allowed_ticks(m, ticks_per_block) if parking else 0.0
                if f < m - lag:
                    w[m][f] = 0.0
                    continue
                acc = 0.0
                for i in range(0, finalization_depth - f):
                    acc += probs[i] * w[m + 1][f + i]
                acc += probs_above[finalization_depth - f]
                w[m][f] = acc

    return w[0][0]


# --------------------------------------------------------------------------
# Double-spend (Satoshi baseline)
# --------------------------------------------------------------------------
def dspart(z: int, q: float, k: int) -> float:
    """Direct port of ``dspart``."""
    p = 1.0 - q
    lam = (z + 1) * q / p
    a = lam ** k / (math.factorial(k) * math.exp(lam))
    b = 1.0 - (q / p) ** (z + 1 - k)
    return a * b


def doublespend_attack(z: int, q: float) -> float:
    """Direct port of ``doublespendAttack`` (strict: attacker must exceed)."""
    if q > 0.5:
        return 1.0
    return 1.0 - sum(dspart(z, q, k) for k in range(z + 2))


def doublespend_attack_tie(z: int, q: float) -> float:
    """Direct port of ``doublespendAttackTie`` (tie counts as success)."""
    if q > 0.5:
        return 1.0
    return 1.0 - sum(dspart(z, q, k) for k in range(z + 1))


# --------------------------------------------------------------------------
# Limited-time double spend with optional parking
# --------------------------------------------------------------------------
def limited_double_spend_attack_iter(
    q: float,
    embargo: int,
    max_depth: int,
    parking: bool = True,
    ticks_per_block: int = 60,
) -> float:
    """Direct port of ``limitedDoubleSpendAttack_iter``.

    The merchant releases after ``embargo`` confirmations; ``max_depth`` is
    the pre-parking confirmation depth under test (with ``parking`` the
    effective computational depth is doubled).
    """
    p = 1.0 - q
    calc_depth = max_depth * 2 if parking else max_depth
    probs = poisson_probs(q / p, calc_depth)

    w = [[0.0] * (calc_depth + 1) for _ in range(max_depth + 1)]
    for m in range(max_depth - 1, -1, -1):
        need = penalty_blocks(m, ticks_per_block) if parking else m + 1
        for f in range(calc_depth, -1, -1):
            if f >= need and f > embargo:
                w[m][f] = 1.0
                continue
            n = calc_depth - f
            if n <= 0:
                w[m][f] = 1.0
                continue
            acc = 1.0 - sum(probs[:n])
            for i in range(n):
                acc += probs[i] * w[m + 1][f + i]
            w[m][f] = acc
    return w[0][0]


# --------------------------------------------------------------------------
# Curve helpers (data only; figures live in plotting.py)
# --------------------------------------------------------------------------
def fork_matching_curve(
    n_points: int = 160, start: float = 0.01, stop: float = 0.99
) -> dict[str, np.ndarray]:
    """Fork-matching probabilities vs attacker share for both regimes.

    Returns arrays keyed ``x``, ``bch_park``, ``bch_nopark``, ``new_park``,
    ``new_nopark`` -- matching the proponent's ``fork_attack_plot.png``.
    """
    x = np.linspace(start, stop, n_points)
    out = {
        "x": x,
        "bch_park": np.array([fin_park_fork_two_sided(q, BCH_FIN, True, BCH_TPB) for q in x]),
        "bch_nopark": np.array(
            [fin_park_fork_two_sided(q, BCH_FIN, False, BCH_TPB) for q in x]
        ),
        "new_park": np.array([fin_park_fork_two_sided(q, NEW_FIN, True, NEW_TPB) for q in x]),
        "new_nopark": np.array(
            [fin_park_fork_two_sided(q, NEW_FIN, False, NEW_TPB) for q in x]
        ),
    }
    return out


def double_spend_curve(
    embargo: int,
    n_points: int = 160,
    start: float = 0.01,
    stop: float = 0.90,
) -> dict[str, np.ndarray]:
    """Double-spend probability vs attacker share for one embargo config.

    ``bch_embargo`` and ``new_embargo`` are the parking-enabled confirmation
    depths. The Satoshi analytic baseline uses ``doublespend_attack``;
    ``embargo == new_embargo`` yields a single baseline curve.
    """
    x = np.linspace(start, stop, n_points)
    bch_embargo, new_embargo = BCH_FIN, NEW_FIN
    return {
        "x": x,
        "satoshi_bch": np.array([doublespend_attack(embargo, q) for q in x]),
        "satoshi_new": np.array([doublespend_attack(new_embargo, q) for q in x]),
        "bch_park": np.array(
            [limited_double_spend_attack_iter(q, embargo, bch_embargo, True, BCH_TPB) for q in x]
        ),
        "bch_nopark": np.array(
            [limited_double_spend_attack_iter(q, embargo, bch_embargo, False, BCH_TPB) for q in x]
        ),
        "new_park": np.array(
            [limited_double_spend_attack_iter(q, embargo, new_embargo, True, NEW_TPB) for q in x]
        ),
        "new_nopark": np.array(
            [limited_double_spend_attack_iter(q, embargo, new_embargo, False, NEW_TPB) for q in x]
        ),
    }