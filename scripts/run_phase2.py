#!/usr/bin/env python
"""Run Phase II (R1-R8): robustness / adversarial scenarios.

Usage:
    python scripts/run_phase2.py [--trials N] [--config PATH] [--figures]
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
    results = EX.run_phase2(cfg, trials=trials)
    frame = EX.collect_records(results.values())

    raw = EX.REPO_ROOT / cfg["output"]["raw_dir"] / "phase2.csv"
    summary = EX.REPO_ROOT / cfg["output"]["tables_dir"] / "phase2_summary.csv"
    EX.save_results(results.values(), raw, summary)
    print(f"Phase II: {len(frame)} rows -> {raw.relative_to(EX.REPO_ROOT)} "
          f"({time.time() - t0:.1f}s)")

    if "R1" in results:
        print("\nR1 deadlines (success before deadline):")
        for label, points in results["R1"].data["curves"].items():
            summary_str = ", ".join(
                f"{int(p['deadline_sec'])}s={p['p_hat']:.4g}" for p in points
            )
            print(f"  {label}: {summary_str}")
    if "R2" in results:
        print("\nR2 start-time scenarios:")
        for s in results["R2"].data["scenarios"]:
            print(f"  {s['scenario']}: {s['p_hat']:.4g}")
    if "R3" in results:
        print("\nR3 abandonment scenarios:")
        for s in results["R3"].data["scenarios"]:
            print(f"  {s['scenario']}: {s['p_hat']:.4g}")

    if args.figures:
        written = PL.make_all_figures(cfg, results=results, trials=trials)
        print(f"\nwrote {len(written)} figures to {cfg['output']['figures_dir']}")


if __name__ == "__main__":
    main()