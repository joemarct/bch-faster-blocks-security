"""Tests for the distribution-based simulator (Simulator B)."""

import pytest

from src import mining as M


def test_probabilities_in_range():
    for q in (0.05, 0.10, 0.30):
        for z in (1, 2, 5):
            r = M.simulate_reversal_distribution(q, z, trials=50_000)
            assert 0.0 <= r.p_hat <= 1.0


def test_majority_certain():
    assert M.simulate_reversal_distribution(0.60, 2, trials=1_000).p_hat == 1.0


def test_zero_attacker_never_reverses():
    assert M.simulate_reversal_distribution(0.0, 3, trials=1_000).successes == 0


def test_monotone_in_depth():
    vals = [M.simulate_reversal_distribution(0.20, z, trials=50_000).p_hat
            for z in (1, 2, 3, 5)]
    assert all(vals[i] >= vals[i + 1] for i in range(len(vals) - 1))


def test_negative_binomial_mean():
    # Mean attacker blocks at acceptance ~ z * q / p.
    q, z = 0.10, 5
    r = M.simulate_reversal_distribution(q, z, trials=200_000)
    assert r.mean_attacker_blocks_at_acceptance == pytest.approx(z * q / (1 - q), abs=0.02)


def test_finite_horizon_le_unlimited():
    unlimited = M.simulate_reversal_distribution(0.10, 2, trials=100_000)
    finite = M.simulate_reversal_distribution(
        0.10, 2, trials=100_000, interval_sec=600, deadline_sec=3600
    )
    assert finite.p_hat <= unlimited.p_hat + 1e-12


def test_interval_invariance_same_seed():
    # With identical seed, T cancels inside the sampler up to floating point.
    r600 = M.simulate_reversal_distribution(0.20, 2, interval_sec=600, trials=100_000)
    r60 = M.simulate_reversal_distribution(0.20, 2, interval_sec=60, trials=100_000)
    assert r600.p_hat == pytest.approx(r60.p_hat, abs=0.01)


def test_same_seed_reproducible():
    a = M.simulate_reversal_distribution(0.15, 2, trials=20_000, seed_label="x")
    b = M.simulate_reversal_distribution(0.15, 2, trials=20_000, seed_label="x")
    assert a.successes == b.successes


def test_invalid_inputs():
    with pytest.raises(ValueError):
        M.simulate_reversal_distribution(0.1, 0)
    with pytest.raises(ValueError):
        M.simulate_reversal_distribution(0.1, 1, "nope")