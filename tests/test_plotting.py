"""Smoke tests for Figures 1-12 (headless Agg backend)."""

from __future__ import annotations

import pytest

from src import experiments as EX
from src import plotting as PL


@pytest.fixture(scope="module")
def cfg(tmp_path_factory):
    cfg = EX.load_config()
    cfg["output"]["figures_dir"] = str(tmp_path_factory.mktemp("figures"))
    return cfg


def test_all_figures_registered():
    assert len(PL.FIGURES) == 12


def test_each_figure_renders(cfg):
    written = PL.make_all_figures(cfg, trials=600)
    assert len(written) == 12
    for path in written.values():
        assert path.exists()
        assert path.stat().st_size > 0


def test_only_subset(cfg):
    written = PL.make_all_figures(cfg, trials=600, only=["fig02_reversal_vs_depth"])
    assert set(written) == {"fig02_reversal_vs_depth"}


def test_figure_accepts_precomputed_results(cfg):
    res = {"P3": EX.p3_decomposition(cfg)}
    written = PL.make_all_figures(cfg, results=res, only=["fig04_deficit_distribution"])
    assert written["fig04_deficit_distribution"].exists()