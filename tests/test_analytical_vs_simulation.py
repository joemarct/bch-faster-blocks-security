"""Cross-validation: analytical vs both simulators (plan section 10, 34).

Required tests #4 (analytical and Monte Carlo agree), #5 (event-driven and
vectorized agree), #6 (changing T preserving q follows the analytical
prediction), #9 (finite horizon <= unlimited horizon).
"""

import math

import pytest

from src import analytical as A
from src import mining as M

TRIALS = 100_000
QS = (0.05, 0.10, 0.20, 0.30, 0.40)
ZS = (1, 2, 3, 5, 10)


def _agree(p_hat: float, ana: float, trials: int, sigmas: float = 4.0) -> bool:
    """Monte Carlo agreement within ``sigmas`` standard errors."""
    se = math.sqrt(max(ana * (1.0 - ana), 1e-12) / trials)
    return abs(p_hat - ana) <= sigmas * se + 1e-9


@pytest.mark.parametrize("q", QS)
@pytest.mark.parametrize("z", ZS)
def test_analytical_vs_distribution_sim(q, z):
    """#4: analytic reversal probability agrees with Monte Carlo to ~4 sigma."""
    ana = A.nakamoto_reversal_probability(q, z, "tie_win")
    sim = M.simulate_reversal_distribution(q, z, "tie_win", trials=TRIALS)
    assert _agree(sim.p_hat, ana, TRIALS), (
        f"q={q} z={z}: analytic={ana:.6f} sim={sim.p_hat:.6f} "
        f"CI=[{sim.ci_lower:.6f},{sim.ci_upper:.6f}]"
    )


@pytest.mark.parametrize("q", (0.05, 0.10, 0.20, 0.30))
@pytest.mark.parametrize("z", (1, 2, 3, 5))
def test_event_driven_vs_vectorized(q, z):
    """#5: the two independent simulators agree within combined uncertainty."""
    a = M.simulate_reversal_bernoulli(q, z, "tie_win", trials=TRIALS, failure_lag=150)
    b = M.simulate_reversal_distribution(q, z, "tie_win", trials=TRIALS)
    se = math.sqrt(
        max(a.p_hat * (1 - a.p_hat), 1e-12) / TRIALS
        + max(b.p_hat * (1 - b.p_hat), 1e-12) / TRIALS
    )
    assert abs(a.p_hat - b.p_hat) <= 4.0 * se + 1e-9


def test_event_driven_vs_analytical():
    """#4 (event-driven side) for a representative cell."""
    ana = A.nakamoto_reversal_probability(0.10, 2, "tie_win")
    sim = M.simulate_reversal_bernoulli(0.10, 2, "tie_win", trials=TRIALS, failure_lag=200)
    assert _agree(sim.p_hat, ana, TRIALS, sigmas=4.0)


def test_interval_rescaling_preserves_q():
    """#6: q is the next-block probability regardless of T, so the reversal
    probability is T-free. Verify both simulators and the analytic model."""
    ana = A.nakamoto_reversal_probability(0.20, 2, "tie_win")
    r600 = M.simulate_reversal_distribution(0.20, 2, "tie_win", interval_sec=600, trials=TRIALS)
    r60 = M.simulate_reversal_distribution(0.20, 2, "tie_win", interval_sec=60, trials=TRIALS)
    for r in (r600, r60):
        assert _agree(r.p_hat, ana, TRIALS)


def test_finite_horizon_bounded_by_unlimited():
    """#9"""
    for q in (0.10, 0.20, 0.30):
        unlimited = M.simulate_reversal_distribution(q, 2, trials=TRIALS)
        finite = M.simulate_reversal_distribution(
            q, 2, trials=TRIALS, interval_sec=600, deadline_sec=1800
        )
        assert finite.p_hat <= unlimited.p_hat + 1e-12


def test_finite_horizon_shrinks_with_shorter_deadline():
    long_d = M.simulate_reversal_distribution(
        0.20, 2, trials=TRIALS, interval_sec=600, deadline_sec=7200
    )
    short_d = M.simulate_reversal_distribution(
        0.20, 2, trials=TRIALS, interval_sec=600, deadline_sec=600
    )
    assert short_d.p_hat <= long_d.p_hat + 1e-12


def test_strict_policy_below_tie_policy():
    ana_tie = A.nakamoto_reversal_probability(0.20, 2, "tie_win")
    ana_strict = A.nakamoto_reversal_probability(0.20, 2, "strict")
    assert ana_strict < ana_tie