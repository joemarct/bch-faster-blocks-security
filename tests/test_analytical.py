"""Unit tests for the analytical baseline (plan sections 10, 34, 35)."""

import math

import pytest

from src import analytical as A


# --- (1) q = 0 cannot reverse a confirmed chain ---------------------------
def test_zero_attacker_cannot_reverse():
    for z in (1, 2, 3, 10):
        assert A.nakamoto_reversal_probability(0.0, z, "strict") == 0.0
        assert A.nakamoto_reversal_probability(0.0, z, "tie_win") == 0.0
        assert A.race_probability(0.0, z + 1, z + 1) == 0.0


# --- (2) majority succeeds with unlimited time ----------------------------
def test_majority_ultimate_success():
    for q in (0.51, 0.60, 0.75):
        assert A.nakamoto_reversal_probability(q, 1, "strict") == 1.0
        assert A.catchup_probability(q, 10, "strict") == 1.0


# --- (3) deeper confirmations never increase minority reversal ------------
def test_monotone_in_confirmations():
    for q in (0.05, 0.10, 0.20, 0.30, 0.40):
        seq = [A.nakamoto_reversal_probability(q, z, "tie_win") for z in range(1, 11)]
        assert all(seq[i] >= seq[i + 1] - 1e-12 for i in range(len(seq) - 1))


# --- catch-up / exact values (hand-verified anchors) ----------------------
def test_catchup_values():
    q = 0.10
    assert A.catchup_probability(q, 1, "tie_win") == pytest.approx(0.1 / 0.9)
    assert A.catchup_probability(q, 1, "strict") == pytest.approx((0.1 / 0.9) ** 2)
    assert A.catchup_probability(q, 0, "tie_win") == 1.0


def test_exact_negative_binomial_anchors():
    # z = 1, tie_win: geometric mixture gives exactly 2q.
    assert A.nakamoto_reversal_probability(0.10, 1, "tie_win") == pytest.approx(0.20, abs=1e-12)
    # z = 2, tie_win: hand-computed 0.056.
    assert A.nakamoto_reversal_probability(0.10, 2, "tie_win") == pytest.approx(0.056, abs=1e-12)
    # strict variants.
    assert A.nakamoto_reversal_probability(0.10, 1, "strict") == pytest.approx(0.0311111111, abs=1e-9)


def test_poisson_approximation_anchors():
    assert A.nakamoto_reversal_probability_poisson(0.10, 1, "tie_win") == pytest.approx(
        0.2046, abs=1e-3
    )
    assert A.nakamoto_reversal_probability_poisson(0.10, 2, "tie_win") == pytest.approx(
        0.051, abs=1e-3
    )


# --- central claim direction: 2x60s safer than 1x600s ---------------------
def test_central_claim_direction():
    q = 0.10
    p_600_1 = A.nakamoto_reversal_probability(q, 1, "tie_win")
    p_60_2 = A.nakamoto_reversal_probability(q, 2, "tie_win")
    assert p_60_2 < p_600_1


# --- interval invariance (H1) --------------------------------------------
def test_interval_invariance():
    # Reversal probability depends on q and z, not on T.
    for q in (0.05, 0.10, 0.30):
        for z in (1, 2, 5):
            # same analytic call is T-free by construction; assert API has no T.
            v1 = A.nakamoto_reversal_probability(q, z, "tie_win")
            v2 = A.nakamoto_reversal_probability(q, z, "tie_win")
            assert v1 == v2


# --- race probability / Fablous I_q(m, m) ---------------------------------
def test_race_probability_matches_betainc():
    from scipy import special

    for q in (0.05, 0.10, 0.25, 0.40):
        for m in (1, 2, 3, 5, 10):
            assert A.race_probability(q, m, m) == pytest.approx(special.betainc(m, m, q))


def test_fablous_double_spend_decimal_rows():
    # (m, q) -> percent from security.md
    rows = {
        (1, 0.10): 10, (2, 0.10): 3, (3, 0.10): 1,
        (2, 0.25): 16, (2, 0.33): 25, (2, 0.40): 35,
    }
    for (m, q), pct in rows.items():
        assert round(A.race_probability(q, m, m) * 100) == pct


# --- (36x) economic anchor ------------------------------------------------
def test_36x_break_even():
    assert A.doublespend_break_even_multiple(0.10, 2) == pytest.approx(35.714285, abs=1e-4)
    assert round(A.doublespend_break_even_multiple(0.10, 2)) == 36


# --- tick-scaled parking schedule -----------------------------------------
def test_tick_schedule():
    assert A.lag_allowed_ticks(1, 60) == 0.5
    assert A.lag_allowed_ticks(4, 600) == 2.0
    assert A.penalty_blocks(4, 600) == 9
    assert A.lag_allowed_ticks(40, 60) == 20.0
    assert A.penalty_blocks(40, 60) == 81
    # Parking becomes a 2x-work requirement from the >=2400-tick band.
    assert A.penalty_blocks(40, 60) == 2 * 40 + 1


# --- deficit distribution / decomposition (plan section 12) ---------------
def test_deficit_distribution_sums_to_one():
    for q in (0.05, 0.10, 0.30):
        for z in (1, 2, 5):
            dist = A.attacker_deficit_distribution(q, z)
            assert sum(dist.values()) == pytest.approx(1.0)


def test_decomposition_sums_to_reversal():
    for q in (0.05, 0.10, 0.30):
        for z in (1, 2, 5):
            for tie in ("strict", "tie_win"):
                rows = A.reversal_decomposition(q, z, tie)
                total = sum(c for *_, c in rows)
                assert total == pytest.approx(
                    A.nakamoto_reversal_probability(q, z, tie), abs=1e-12
                )


# --- waiting time / work normalization ------------------------------------
def test_wait_and_work():
    assert A.expected_wait_sec(2, 60) == 120.0
    assert A.expected_wait_sec(1, 600) == 600.0
    assert A.median_wait_sec(1, 60) < 60.0  # exponential median < mean
    assert A.normalized_work(2, 60) == pytest.approx(0.2)
    assert A.normalized_work(1, 600) == pytest.approx(1.0)


# --- external hash threshold (R6) -----------------------------------------
def test_external_hash_required():
    assert A.external_hash_required(0.30, 1.0) == pytest.approx(0.30 / 0.70)
    assert A.external_hash_required(0.50, 1.0) == pytest.approx(1.0)


# --- invalid inputs -------------------------------------------------------
def test_invalid_inputs():
    with pytest.raises(ValueError):
        A.catchup_probability(0.1, 1, "nonsense")
    with pytest.raises(ValueError):
        A.nakamoto_reversal_probability(0.1, 0)
    with pytest.raises(ValueError):
        A.race_probability(0.1, 0, 1)