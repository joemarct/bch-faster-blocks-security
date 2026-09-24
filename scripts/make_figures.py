#!/usr/bin/env python
"""Render Figures 1-12 from plan section 36.

Usage:
    python scripts/make_figures.py [--trials N] [--config PATH] [--only NAME ...]
"""

from __future__ import annotations

import argparse

import _bootstrap  # noqa: F401  (sys.path)

from src import experiments as EX
from src import plotting as PL


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=None)
    parser.add_argument("--trials", type=int, default=None)
    parser.add_argument("--only", nargs="*", default=None, help="figure keys to render")
    args = parser.parse_args()

    cfg = EX.load_config(args.config)
    written = PL.make_all_figures(
        cfg, results=None, trials=args.trials, only=args.only
    )
    for name, path in written.items():
        print(f"{name}: {path}")


if __name__ == "__main__":
    main()