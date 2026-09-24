"""Reproducibility tests (tests #10, #11; plan section 31)."""

import numpy as np
import pytest

from src import mining as M
from src.statistics import derive_seed, make_rng, wilson_interval


def test_same_seed_reproduces_everything():
    """#10"""
    a = M.simulate_reversal_distribution(0.10, 2, trials=20_000, master_seed=42)
    b = M.simulate_reversal_distribution(0.10, 2, trials=20_000, master_seed=42)
    assert a.successes == b.successes
    assert a.p_hat == b.p_hat
    assert a.mean_deficit_at_acceptance == b.mean_deficit_at_acceptance


def test_different_seeds_statistically_compatible():
    """#11"""
    a = M.simulate_reversal_distribution(0.20, 2, trials=100_000, master_seed=1)
    b = M.simulate_reversal_distribution(0.20, 2, trials=100_000, master_seed=2)
    assert not (a.ci_upper < b.ci_lower or b.ci_upper < a.ci_lower)


def test_derive_seed_deterministic_and_distinct():
    assert derive_seed(1, "a") == derive_seed(1, "a")
    assert derive_seed(1, "a") != derive_seed(1, "b")
    assert derive_seed(1, "a") != derive_seed(2, "a")


def test_make_rng_unaffected_by_hash_seed():
    # Explicit seeds -> reproducible draws regardless of PYTHONHASHSEED.
    r1 = make_rng(20250924, "labels", 0.1, 2)
    r2 = make_rng(20250924, "labels", 0.1, 2)
    np.testing.assert_array_equal(r1.random(100), r2.random(100))


def test_wilson_interval_properties():
    lo, hi = wilson_interval(50, 100)
    assert lo < 0.5 < hi
    assert 0.0 <= lo <= hi <= 1.0
    # Zero successes -> non-degenerate upper bound, lower bound at 0.
    lo0, hi0 = wilson_interval(0, 1000)
    assert lo0 == pytest.approx(0.0, abs=1e-12)
    assert 0.0 < hi0 < 0.01
    # All successes.
    lo1, hi1 = wilson_interval(1000, 1000)
    assert hi1 == pytest.approx(1.0)
    assert lo1 > 0.99


def test_code_version_runs():
    from src.statistics import code_version

    v = code_version()
    assert isinstance(v, str) and len(v) > 0