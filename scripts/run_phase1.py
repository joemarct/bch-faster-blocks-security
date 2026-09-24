#!/usr/bin/env python
"""Run Phase I (P0-P8): reproduce the proponent's core claims.

Usage:
    python scripts/run_phase1.py [--trials N] [--config PATH] [--figures]
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
    parser.add_argument("--figures", action="store_true", help="also render figures")
    args = parser.parse_args()

    cfg = EX.load_config(args.config)
    trials = args.trials
    t0 = time.time()
    results = EX.run_phase1(cfg, trials=trials)
    frame = EX.collect_records(results.values())

    raw = EX.REPO_ROOT / cfg["output"]["raw_dir"] / "phase1.csv"
    summary = EX.REPO_ROOT / cfg["output"]["tables_dir"] / "phase1_summary.csv"
    EX.save_results(results.values(), raw, summary)
    print(f"Phase I: {len(frame)} rows -> {raw.relative_to(EX.REPO_ROOT)} "
          f"({time.time() - t0:.1f}s)")

    mvp = EX.mvp_frame(cfg, trials=trials)
    print("\nSection 39 minimum-viable table (q = 0.10):")
    print(mvp.to_string(index=False))

    if args.figures:
        written = PL.make_all_figures(cfg, results=results, trials=trials)
        print(f"\nwrote {len(written)} figures to {cfg['output']['figures_dir']}")


if __name__ == "__main__":
    main()