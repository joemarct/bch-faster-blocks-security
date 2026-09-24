"""External / temporary hashpower tests R4-R6 (required test #12)."""

import numpy as np
import pytest

from src.analytical import external_hash_required
from src.external_hash import (
    _share_schedule,
    acquisition_delay_grid,
    temporary_hash_reversal,
    temporary_majority_grid,
)


def test_share_schedule_activates_and_deactivates():
    """Required test #12: temporary hashpower turns on and off on schedule."""
    t = np.array([0.0, 5.0, 10.0, 19.0, 20.0, 25.0, 100.0])
    sched = _share_schedule(t, q0=0.05, q_active=0.60, activation=10.0, duration=10.0)
    assert sched[0] == pytest.approx(0.05)  # before
    assert sched[1] == pytest.approx(0.05)
    assert sched[2] == pytest.approx(0.60)  # at activation
    assert sched[3] == pytest.approx(0.60)  # inside window
    assert sched[4] == pytest.approx(0.05)  # at deactivation (exclusive)
    assert sched[5] == pytest.approx(0.05)  # after
    assert sched[6] == pytest.approx(0.05)


def test_zero_duration_is_pure_q0():
    r = temporary_hash_reversal(
        q0=0.10, q_active=0.90, acquisition_delay_sec=0.0, active_duration_sec=0.0,
        z=1, deadline_sec=86_400, interval_sec=60, trials=20_000,
    )
    # Identical to a constant 0.10 attacker; low but nonzero.
    assert 0.0 < r.p_hat < 0.4


def test_surge_duration_increases_success():
    short = temporary_hash_reversal(
        q0=0.05, q_active=0.70, acquisition_delay_sec=0.0, active_duration_sec=60.0,
        z=1, deadline_sec=86_400, interval_sec=60, trials=20_000,
    )
    long = temporary_hash_reversal(
        q0=0.05, q_active=0.70, acquisition_delay_sec=0.0, active_duration_sec=7_200.0,
        z=1, deadline_sec=86_400, interval_sec=60, trials=20_000,
    )
    assert long.p_hat > short.p_hat


def test_acquisition_delay_hurts():
    early = temporary_hash_reversal(
        q0=0.05, q_active=0.60, acquisition_delay_sec=0.0, active_duration_sec=600.0,
        z=2, deadline_sec=86_400, interval_sec=60, trials=20_000,
    )
    late = temporary_hash_reversal(
        q0=0.05, q_active=0.60, acquisition_delay_sec=3_600.0, active_duration_sec=600.0,
        z=2, deadline_sec=86_400, interval_sec=60, trials=20_000,
    )
    assert late.p_hat < early.p_hat


def test_majority_surge_can_succeed():
    r = temporary_hash_reversal(
        q0=0.05, q_active=0.75, acquisition_delay_sec=0.0, active_duration_sec=86_400.0,
        z=1, deadline_sec=86_400, interval_sec=60, trials=5_000,
    )
    assert r.p_hat > 0.3


def test_external_hash_required():
    assert external_hash_required(0.5, 1.0) == pytest.approx(1.0)
    assert external_hash_required(0.10, 1.0) == pytest.approx(0.10 / 0.90)
    assert external_hash_required(0.90, 1.0) == pytest.approx(9.0)


def test_grids_run_and_key():
    grid = temporary_majority_grid(
        q0=0.05, shares=[0.6, 0.8], durations_sec=[60.0, 3600.0],
        z=1, deadline_sec=86_400, interval_sec=60, trials=2_000,
    )
    assert set(grid.keys()) == {(0.6, 60.0), (0.6, 3600.0), (0.8, 60.0), (0.8, 3600.0)}
    dgrid = acquisition_delay_grid(
        q0=0.05, shares=[0.6], delays_sec=[0.0, 600.0],
        active_duration_sec=600.0, z=1, deadline_sec=86_400, interval_sec=60, trials=2_000,
    )
    assert set(dgrid.keys()) == {(0.0, 0.6), (600.0, 0.6)}
