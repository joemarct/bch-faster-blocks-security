"""Chainwork vs confirmations, and waiting-time rescaling (tests #6, #7, #8)."""

import pytest

from src import analytical as A
from src import mining as M


def test_cumulative_work_normalization():
    """#8: W_60 = 0.1, W_600 = 1.0; equal counts scale linearly."""
    assert A.normalized_work(1, 600) == pytest.approx(1.0)
    assert A.normalized_work(1, 60) == pytest.approx(0.1)
    assert A.normalized_work(10, 60) == pytest.approx(1.0)
    assert A.normalized_work(2, 60) == pytest.approx(0.2)


def test_equal_expected_chainwork_policies():
    """Policies with equal expected normalized work (600x1 vs 60x10)."""
    assert A.normalized_work(1, 600) == A.normalized_work(10, 60)
    assert A.normalized_work(2, 600) == A.normalized_work(20, 60)
    assert A.normalized_work(3, 600) == A.normalized_work(30, 60)


def test_more_confirmations_safer_at_equal_work():
    """At equal expected chainwork, 10x60s is safer than 1x600s (depth effect)."""
    q = 0.10
    p_600_1 = A.nakamoto_reversal_probability(q, 1, "tie_win")
    p_60_10 = A.nakamoto_reversal_probability(q, 10, "tie_win")
    assert p_60_10 < p_600_1


def test_waiting_time_scales_with_interval():
    """#7: wall-clock waiting distributions change appropriately with T."""
    assert A.expected_wait_sec(2, 60) == 120.0
    assert A.expected_wait_sec(2, 600) == 1200.0
    # Median of Erlang(2, 1/T) scales linearly in T.
    assert A.median_wait_sec(2, 600) == pytest.approx(10 * A.median_wait_sec(2, 60))


def test_expected_wait_ratio_is_ten():
    for z in (1, 2, 3, 5, 10):
        assert A.expected_wait_sec(z, 600) / A.expected_wait_sec(z, 60) == pytest.approx(10.0)


def test_simulated_acceptance_depth_tracks_policy():
    # Larger z at 60s corresponds to the same or longer nominal wait as smaller
    # z at 600s only when z_60 >= 10 * z_600.
    r = M.simulate_reversal_distribution(0.10, 10, interval_sec=60, trials=50_000)
    assert r.mean_acceptance_blocks == 10