"""Robustness tests R1-R3, R8 (plan sections 19-22, 26)."""

import pytest

from src.analytical import nakamoto_reversal_probability
from src.attacks import (
    cost_of_normalized_work,
    cost_to_reach_confirmations,
    finite_horizon_reversal,
    majority_cost_per_unit_time,
)
from src.mining import simulate_reversal_distribution


def test_finite_horizon_bounded_by_unlimited():
    unlimited = nakamoto_reversal_probability(0.10, 2, "tie_win")
    finite = finite_horizon_reversal(
        0.10, 2, deadline_sec=3600, interval_sec=60, trials=20_000
    )
    assert finite.p_hat <= unlimited + 0.02


def test_longer_deadline_increases_success():
    short = finite_horizon_reversal(0.20, 1, deadline_sec=300, interval_sec=60, trials=40_000)
    long = finite_horizon_reversal(0.20, 1, deadline_sec=86_400, interval_sec=60, trials=40_000)
    assert long.p_hat > short.p_hat


def test_zero_attacker_never_succeeds():
    r = finite_horizon_reversal(0.0, 2, deadline_sec=3600, trials=5_000)
    assert r.successes == 0


def test_majority_quick_success():
    r = finite_horizon_reversal(0.60, 1, deadline_sec=86_400, interval_sec=60, trials=2_000)
    assert r.p_hat > 0.5


def test_premining_lead_helps():
    base = finite_horizon_reversal(
        0.15, 3, deadline_sec=86_400, interval_sec=60, start_policy="simultaneous", trials=40_000
    )
    lead = finite_horizon_reversal(
        0.15, 3, deadline_sec=86_400, interval_sec=60,
        start_policy="premining", premining_lead=2, trials=40_000,
    )
    assert lead.p_hat > base.p_hat


def test_reactive_delay_hurts():
    base = finite_horizon_reversal(
        0.20, 2, deadline_sec=86_400, interval_sec=60, start_policy="simultaneous", trials=40_000
    )
    delayed = finite_horizon_reversal(
        0.20, 2, deadline_sec=86_400, interval_sec=60,
        start_policy="reactive", start_delay_sec=600, trials=40_000,
    )
    assert delayed.p_hat < base.p_hat


def test_abandonment_monotonic():
    tight = finite_horizon_reversal(
        0.15, 2, deadline_sec=86_400, interval_sec=60, abandonment_deficit=2, trials=40_000
    )
    loose = finite_horizon_reversal(
        0.15, 2, deadline_sec=86_400, interval_sec=60, abandonment_deficit=50, trials=40_000
    )
    assert tight.p_hat <= loose.p_hat + 0.01


def test_interval_invariance_of_block_horizon():
    # Same wall-clock deadline, different intervals: the *block* budget scales,
    # so success probabilities are close (both use the same q).
    slow = finite_horizon_reversal(0.20, 1, deadline_sec=36_000, interval_sec=600, trials=40_000)
    fast = finite_horizon_reversal(0.20, 1, deadline_sec=36_000, interval_sec=60, trials=40_000)
    assert abs(slow.p_hat - fast.p_hat) < 0.05


def test_invalid_start_policy():
    with pytest.raises(ValueError):
        finite_horizon_reversal(0.1, 1, deadline_sec=60, start_policy="nope")


def test_cost_accounting_r8():
    per_sec = majority_cost_per_unit_time(0.1, 100.0, 1e-6)
    assert per_sec == pytest.approx(0.1 * 100.0 * 1e-6)
    # Equal wall-clock cost does NOT arrive at equal confirmation count.
    slow = cost_to_reach_confirmations(1, 600.0, 100.0, 1e-6)
    fast = cost_to_reach_confirmations(1, 60.0, 100.0, 1e-6)
    assert slow == pytest.approx(10 * fast)
    # Equal *chainwork* costs equally.
    assert cost_of_normalized_work(1, 600.0, 600.0, 100.0, 1e-6) == pytest.approx(
        cost_of_normalized_work(10, 60.0, 600.0, 100.0, 1e-6)
    )
