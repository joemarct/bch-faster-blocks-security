"""Tests for the discrete event-driven Bernoulli simulator (Simulator A)."""

import numpy as np
import pytest

from src import analytical as A
from src import mining as M


def test_probabilities_in_range():
    for q in (0.05, 0.10, 0.30):
        for z in (1, 2, 5):
            r = M.simulate_reversal_bernoulli(q, z, trials=20_000, failure_lag=150)
            assert 0.0 <= r.p_hat <= 1.0
            assert r.trials == 20_000
            assert r.successes + (r.trials - r.successes) == r.trials


def test_majority_certain():
    r = M.simulate_reversal_bernoulli(0.60, 2, trials=5_000)
    assert r.p_hat == 1.0


def test_zero_attacker_never_reverses():
    r = M.simulate_reversal_bernoulli(0.0, 3, trials=5_000)
    assert r.successes == 0


def test_acceptance_depth_matches_z():
    for z in (1, 2, 4):
        r = M.simulate_reversal_bernoulli(0.10, z, trials=20_000, failure_lag=150)
        assert r.mean_acceptance_blocks == pytest.approx(z, abs=1e-9)


def test_monotone_in_depth():
    vals = [M.simulate_reversal_bernoulli(0.20, z, trials=40_000, failure_lag=150).p_hat
            for z in (1, 2, 3, 5)]
    assert all(vals[i] >= vals[i + 1] for i in range(len(vals) - 1))


def test_anchor_q10_z1():
    r = M.simulate_reversal_bernoulli(0.10, 1, trials=100_000, failure_lag=200)
    assert r.ci_lower <= 0.20 <= r.ci_upper


def test_same_seed_reproducible():
    a = M.simulate_reversal_bernoulli(0.15, 2, trials=10_000, seed_label="x")
    b = M.simulate_reversal_bernoulli(0.15, 2, trials=10_000, seed_label="x")
    assert a.successes == b.successes
    c = M.simulate_reversal_bernoulli(0.15, 2, trials=10_000, seed_label="y")
    assert c.seed != a.seed


def test_strict_not_greater_than_tie_win():
    tie = M.simulate_reversal_bernoulli(0.20, 2, "tie_win", trials=40_000, failure_lag=150)
    strict = M.simulate_reversal_bernoulli(0.20, 2, "strict", trials=40_000, failure_lag=150)
    assert strict.p_hat <= tie.p_hat + 1e-9


def test_invalid_inputs():
    with pytest.raises(ValueError):
        M.simulate_reversal_bernoulli(0.1, 0)
    with pytest.raises(ValueError):
        M.simulate_reversal_bernoulli(0.1, 1, "nope")