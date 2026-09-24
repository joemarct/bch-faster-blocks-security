#!/usr/bin/env python
"""Run every experiment (Phases I and II), write the master table and figures.

Usage:
    python scripts/run_all.py [--trials N] [--config PATH] [--no-figures]
"""

from __future__ import annotations

import argparse
import time

import _bootstrap  # noqa: F401  (sys.path)

from src import experiments as EX
from src import plotting as PL


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=None, help="path to a YAML config")
    parser.add_argument("--trials", type=int, default=None, help="Monte Carlo trials")
    parser.add_argument("--no-figures", action="store_true")
    args = parser.parse_args()

    cfg = EX.load_config(args.config)
    trials = args.trials
    t0 = time.time()

    phase1 = EX.run_phase1(cfg, trials=trials)
    phase2 = EX.run_phase2(cfg, trials=trials)
    results = {**phase1, **phase2}
    frame = EX.collect_records(results.values())

    master = EX.REPO_ROOT / cfg["output"]["master_results"]
    summary = EX.REPO_ROOT / cfg["output"]["tables_dir"] / "master_summary.csv"
    EX.save_results(results.values(), master, summary)
    print(f"master: {len(frame)} rows -> {master.relative_to(EX.REPO_ROOT)} "
          f"({time.time() - t0:.1f}s)")

    print("\nSection 39 MVP table (q = 0.10):")
    print(EX.mvp_frame(cfg, trials=trials).to_string(index=False))

    if not args.no_figures:
        written = PL.make_all_figures(cfg, results=results, trials=trials)
        print(f"\nwrote {len(written)} figures to {cfg['output']['figures_dir']}")


if __name__ == "__main__":
    main()