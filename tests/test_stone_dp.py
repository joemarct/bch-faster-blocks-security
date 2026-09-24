"""Regression tests for the faithful Stone-DP port against Fablous tables."""

import pytest

from src import analytical as A
from src import stone_dp as S


def _bisect(fn, target, lo=0.01, hi=0.99, iters=60):
    for _ in range(iters):
        mid = (lo + hi) / 2
        if fn(mid) < target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


# --- headline reproduction numbers from security.md -----------------------
def test_fork_matching_even_odds_thresholds():
    bch = _bisect(lambda q: S.fin_park_fork_two_sided(q, S.BCH_FIN, True, S.BCH_TPB), 0.5)
    new = _bisect(lambda q: S.fin_park_fork_two_sided(q, S.NEW_FIN, True, S.NEW_TPB), 0.5)
    # Proponent: ~52% -> ~57%; curves converge near 0.60.
    assert 0.50 <= bch <= 0.53
    assert 0.55 <= new <= 0.59
    assert new > bch


def test_fork_matching_10pct_thresholds():
    bch = _bisect(lambda q: S.fin_park_fork_two_sided(q, S.BCH_FIN, True, S.BCH_TPB), 0.10)
    new = _bisect(lambda q: S.fin_park_fork_two_sided(q, S.NEW_FIN, True, S.NEW_TPB), 0.10)
    # Proponent: ~33% -> ~45%.
    assert 0.31 <= bch <= 0.35
    assert 0.43 <= new <= 0.47


def test_new_regime_safer_than_bch_submajority():
    # At sub-majority hashrates the parked new regime is far safer than the
    # parked current-BCH regime, and the attacker is well below even odds.
    for q in (0.30, 0.40, 0.45):
        bch = S.fin_park_fork_two_sided(q, S.BCH_FIN, True, S.BCH_TPB)
        new = S.fin_park_fork_two_sided(q, S.NEW_FIN, True, S.NEW_TPB)
        assert new < bch
    assert S.fin_park_fork_two_sided(0.45, S.NEW_FIN, True, S.NEW_TPB) < 0.5


def test_fork_matching_monotone_in_hashrate():
    prev = -1.0
    for q in (0.05, 0.10, 0.20, 0.30, 0.40, 0.50):
        v = S.fin_park_fork_two_sided(q, S.BCH_FIN, True, S.BCH_TPB)
        assert v >= prev - 1e-12
        prev = v


# --- direct port sanity ---------------------------------------------------
def test_dspart_and_doublespend_port():
    # q > 0.5 saturates.
    assert S.doublespend_attack(3, 0.6) == 1.0
    assert S.doublespend_attack_tie(3, 0.6) == 1.0
    # Both are probabilities.
    for q in (0.05, 0.10, 0.25, 0.40):
        for z in (1, 3, 6):
            ps = S.doublespend_attack(z, q)
            pt = S.doublespend_attack_tie(z, q)
            assert 0.0 <= ps <= 1.0
            assert 0.0 <= pt <= 1.0


def test_limited_double_spend_port_probabilities():
    for q in (0.05, 0.10, 0.25, 0.40):
        for embargo, depth in S.EMBARGO_CONFIGS:
            assert 0.0 <= S.limited_double_spend_attack_iter(q, embargo, depth, True, 60) <= 1.0


def test_majority_hashrate_dominates_fork_matching():
    # Supermajority attacker should win the parked fork-matching contest.
    assert S.fin_park_fork_two_sided(0.75, S.BCH_FIN, True, S.BCH_TPB) > 0.9
    assert S.fin_park_fork_two_sided(0.90, S.NEW_FIN, True, S.NEW_TPB) > 0.9


def test_curve_helpers_shapes():
    fc = S.fork_matching_curve(n_points=11)
    assert all(len(v) == 11 for v in fc.values())
    dc = S.double_spend_curve(1, n_points=11)
    assert all(len(v) == 11 for v in dc.values())