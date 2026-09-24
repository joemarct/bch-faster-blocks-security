"""Tests for experiment orchestration (schema, determinism, claims)."""

from __future__ import annotations

import math

import pytest

from src import experiments as EX
from src.statistics import MASTER_FIELDS


@pytest.fixture(scope="module")
def cfg():
    return EX.load_config()


def test_config_loads(cfg):
    assert cfg["intervals"]["baseline_sec"] == 600
    assert cfg["intervals"]["fast_sec"] == 60
    assert cfg["attacker_shares"]["primary"] == 0.10


def test_mvp_schema_is_complete(cfg):
    res = EX.mvp_table(cfg, trials=2000)
    frame = res.frame()
    # Every master-schema field is present as a column.
    for field in MASTER_FIELDS:
        assert field in frame.columns, field
    assert len(frame) == len(cfg["confirmations"]["policies"])


def test_mvp_claim_two_fast_beat_one_slow(cfg):
    frame = EX.mvp_frame(cfg, trials=20000)
    by_policy = dict(zip(frame["policy"], frame["analytical_reversal_probability"]))
    assert by_policy["60s × 2"] < by_policy["600s × 1"]
    assert by_policy["60s × 3"] < by_policy["60s × 2"]
    assert by_policy["600s × 1"] == pytest.approx(0.20, abs=1e-9)


def test_p5_headline_36x(cfg):
    res = EX.p5_coinbase_claim(cfg)
    assert res.data["headline_36x"] == pytest.approx(35.714, rel=1e-3)


def test_experiments_are_deterministic(cfg):
    a = EX.p2_policy_comparison(cfg, trials=3000)
    b = EX.p2_policy_comparison(cfg, trials=3000)
    assert a.frame().equals(b.frame())


def test_p4_interval_invariance(cfg):
    res = EX.p4_interval_comparison(cfg, trials=4000)
    for cell in res.data["cells"]:
        if cell["z"] == 1:
            assert math.isclose(cell["p_hat"], 0.20, abs_tol=0.03)


def test_collect_records_stacks_all(cfg):
    results = EX.run_phase1(cfg, trials=1000)
    frame = EX.collect_records(results.values())
    assert set(frame["experiment"]) >= {r.name for r in results.values()}
    assert len(frame) > 200


def test_r6_threshold_monotone_in_depth(cfg):
    res = EX.r6_external_threshold(cfg)
    target = res.data["tables"]["0.10"]
    # Deeper confirmation needs more external hash to reach the same target.
    assert target[2] <= target[5] <= target[10]


def test_save_results_roundtrip(cfg, tmp_path):
    res = EX.p5_coinbase_claim(cfg)
    out = tmp_path / "p5.csv"
    frame = EX.save_results([res], out)
    assert out.exists()
    assert len(frame) == len(res.records)