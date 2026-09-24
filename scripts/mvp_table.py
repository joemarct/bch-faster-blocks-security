#!/usr/bin/env python
"""Section 39 minimum-viable table at q = 0.10, as CSV and stdout.

Usage:
    python scripts/mvp_table.py [--trials N] [--config PATH] [--out PATH]
"""

from __future__ import annotations

import argparse

import _bootstrap  # noqa: F401  (sys.path)

from src import experiments as EX


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=None)
    parser.add_argument("--trials", type=int, default=None)
    parser.add_argument("--out", default=None, help="CSV output path")
    args = parser.parse_args()

    cfg = EX.load_config(args.config)
    frame = EX.mvp_frame(cfg, trials=args.trials)

    if args.out:
        from pathlib import Path

        out = Path(args.out)
    else:
        out = EX.REPO_ROOT / cfg["output"]["tables_dir"] / "mvp_table.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(out, index=False)
    print(f"wrote {out}")
    print(frame.to_string(index=False))


if __name__ == "__main__":
    main()