"""Economic model tests (plan section 25 / R7, required test #13)."""

import math

import pytest

from src.economics import (
    EconomicModel,
    attack_value_multiple,
    cost_per_confirmation,
    cost_per_successful_reversal,
    doublespend_break_even_table,
    hashrate_cost_per_second,
    sniping_attack_value,
    sniping_break_even_table,
)


def test_36x_coinbase_reproduction():
    table = doublespend_break_even_table(0.10, [2, 3, 4])
    assert table[2] == pytest.approx(35.714, rel=1e-3)
    assert table[2] == pytest.approx((2 - 1) / 0.028, rel=1e-6)
    # Deeper confirmation requirements need a larger prize to be worth attacking.
    assert table[3] > table[2]
    assert table[4] > table[3]
    assert table[3] == pytest.approx(233.6, rel=0.02)


def test_fablous_break_even_row_m2():
    table = doublespend_break_even_table(0.10, [2])
    assert table[2] == pytest.approx(36.0, rel=0.02)


def test_sniping_break_even_positive_and_decreasing():
    table = sniping_break_even_table(0.10, [(1, 1), (1, 2), (2, 1)])
    assert all(v > 0 for v in table.values())
    # More attacker blocks required (larger m) -> larger prize needed.
    assert table[(1, 2)] > table[(1, 1)]


def test_components_sum_to_expected_value():
    """Required test #13: economic accounting conserves rewards and costs."""
    m = EconomicModel(
        double_spend_value=100.0,
        reference_coinbase=10.0,
        attacker_share=0.1,
        success_probability=0.2,
        expected_attacker_blocks=5.0,
        cost_per_work=1.0,
        success_reward=3.0,
        failure_reward=1.0,
        other_costs=2.0,
        failure_loss=7.0,
    )
    comp = m.components()
    rebuilt = (
        comp["success_gross"]
        + comp["failure_gross"]
        - comp["hashing_cost"]
        - comp["other_costs"]
        - comp["failure_loss"]
    )
    assert rebuilt == pytest.approx(m.expected_value(), rel=1e-12)
    assert m.hashing_cost() == pytest.approx(5.0)


def test_break_even_value_zeroes_ev():
    m = EconomicModel(
        double_spend_value=0.0,
        reference_coinbase=10.0,
        attacker_share=0.1,
        success_probability=0.25,
        expected_attacker_blocks=4.0,
        cost_per_work=1.0,
        other_costs=2.0,
        failure_loss=1.0,
    )
    v = m.break_even_value()
    # cost = 4 + 2 + 1 = 7; V* = 7 / 0.25 = 28
    assert v == pytest.approx(28.0)
    assert m.break_even_multiple() == pytest.approx(2.8)
    m.double_spend_value = v
    assert m.expected_value() == pytest.approx(0.0, abs=1e-12)
    assert not m.profitable()
    m.double_spend_value = v + 1.0
    assert m.profitable()


def test_break_even_infinite_without_success():
    m = EconomicModel(0.0, 10.0, 0.0, 0.0, 5.0)
    assert math.isinf(m.break_even_value())


def test_attack_value_multiple_normalises_work():
    slow = attack_value_multiple(0.1, 2, 0.2, 10.0, interval_sec=600.0)
    fast = attack_value_multiple(0.1, 2, 0.2, 1.0, interval_sec=60.0)
    # Fast block earns 1/10 the reference coinbase and costs 1/10 per block.
    assert fast.reference_coinbase == pytest.approx(0.1)
    assert slow.reference_coinbase == pytest.approx(1.0)
    # Hashing cost is work-normalised: 1 fast block == 0.1 slow blocks of work.
    fast.reference_coinbase = slow.reference_coinbase  # compare like-for-like
    assert fast.hashing_cost() == pytest.approx(slow.hashing_cost())


def test_cost_per_second_independent_of_interval():
    """Claim C4: same hashrate share costs the same per wall-clock second."""
    slow = hashrate_cost_per_second(0.1, total_hashrate=100.0, cost_per_hash_sec=1e-6)
    fast = hashrate_cost_per_second(0.1, total_hashrate=100.0, cost_per_hash_sec=1e-6)
    assert slow == pytest.approx(fast)


def test_cost_per_confirmation_scales_with_interval():
    slow = cost_per_confirmation(1, 600.0, 100.0, 1e-6)
    fast = cost_per_confirmation(10, 60.0, 100.0, 1e-6)
    assert slow == pytest.approx(fast)


def test_cost_per_successful_reversal_infinite_without_success():
    assert math.isinf(cost_per_successful_reversal(0.0, 100.0, 100.0, 1e-6))
    finite = cost_per_successful_reversal(0.5, 600.0, 100.0, 1e-6)
    assert finite > 0


def test_sniping_attack_value_sign():
    # Low prize relative to mining cost -> unprofitable.
    assert sniping_attack_value(0.05, n=1, m=1, coinbase=10.0, reachable_value=1.0) < 0
    # Huge prize -> profitable.
    assert sniping_attack_value(0.40, n=0, m=2, coinbase=10.0, reachable_value=10_000.0) > 0
