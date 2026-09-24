# bch-faster-blocks-security

Independent reproduction and robustness testing of the confirmation-security
claims behind faster Bitcoin Cash blocks (CHIP-2025-03 / Fablous). The project
reproduces the proponent's central result, explains *why* it holds, and then
stress-tests it under attacker models the proposal does not cover.

Guiding principle (plan §43): **reproduce first, explain second, stress-test
third, generalize only as far as the evidence permits.** The code does not take
a position on CHIP activation; it states which claims are supported under which
assumptions (plan §41).

## Install

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Python 3.10+. The core package is `src/`; no compilation step is required.

## Quick start

```bash
# Full run: Phases I + II, master results table, and all 12 figures.
.venv/bin/python scripts/run_all.py --trials 50000

# Just the section-39 minimum-viable table at q = 0.10.
.venv/bin/python scripts/mvp_table.py --trials 100000

# Phase I or Phase II only (optionally with figures).
.venv/bin/python scripts/run_phase1.py --trials 50000 --figures
.venv/bin/python scripts/run_phase2.py --trials 50000

# Render figures from a lighter-weight computation.
.venv/bin/python scripts/make_figures.py --trials 20000
```

`--trials` overrides the config; omit it to use the configured counts
(`monte_carlo.dev_trials` = 100k, `final_trials` = 1M).

## Layout

```
config/defaults.yaml     all parameters and seeds
src/analytical.py        exact negative-binomial / race closed forms
src/stone_dp.py          faithful port of Stone (2020) fork-matching DP
src/mining.py            scalar and vectorized reversal simulators
src/attacks.py           finite-horizon, start-time, abandonment simulators
src/external_hash.py     temporary / delayed external SHA-256 hashpower
src/economics.py         break-even and cost accounting
src/statistics.py        master schema, Wilson CIs, seeds, atomic CSV writer
src/experiments.py       P0-P8 (Phase I) and R1-R8 (Phase II) orchestrators
src/plotting.py          Figures 1-12
scripts/                 CLI entry points
notebooks/               ten narrative notebooks (01..10)
tests/                   pytest suite, incl. analytical-vs-simulation checks
```

Outputs land in `results/raw/` (per-record dumps), `results/tables/` (CSV
summaries and the master table), and `results/figures/` (PNG).

## Experiments

Phase I reproduces the proposal's claims; Phase II stress-tests them.

| ID | What it does | Claim / plan ref |
|---|---|---|
| P0 | Exact analytical baseline across q and confirmation depth | §9 |
| P1 | Validate both simulators against the closed form | §10, C1 |
| P2 | Core policy comparison: 600s×1 vs 60s×1/2/3/5/10 | §11, C2 |
| P3 | Deficit-distribution decomposition of the result | §13, H4 |
| P4 | Interval invariance at fixed confirmation depth | C1 |
| P5 | Reproduce the ~36× coinbase and sniping break-even tables | §14, C3 |
| P6 | Equal expected chainwork across policies | §15, H3 |
| P7 | Equal elapsed time across intervals | §16, H5 |
| P8 | Security/latency frontier | §17 |
| R1 | Finite attack-duration curves | §19, H7 |
| R2 | Attack start-time sensitivity (simultaneous/at-inclusion/reactive/premining) | §20 |
| R3 | Rational abandonment thresholds | §21 |
| R4 | Temporary-majority duration grid | §22 |
| R5 | External-hash acquisition-delay grid | §23 |
| R6 | External hash ratio needed to reach a target success probability | §24, C5 |
| R7 | Break-even transaction value vs confirmation policy | §25 |
| R8 | Cost accounting per policy | §26, C4 |

## Figures

`src/plotting.py` implements Figures 1-12 from plan §36. Each function accepts
pre-computed `ExperimentResult`s (so `run_all.py --figures` does not rerun the
experiments) and otherwise recomputes a lighter-weight version.

## Reproducibility

* All randomness is derived from the single master seed
  `config["seed"]["master"]` (20250924) via `statistics.derive_seed`, so every
  experiment is deterministic for a given config and trial count.
* Every record carries the 29-field master schema (plan §37), including seed,
  tie policy, and `code_version`.
* `tests/test_reproducibility.py` asserts bit-identical reruns.
* Results are written atomically; the master table is append-safe.

Run the suite with:

```bash
.venv/bin/python -m pytest
```

See [CLAIMS.md](CLAIMS.md) for the claim matrix, [HYPOTHESES.md](HYPOTHESES.md)
for the pre-registered hypotheses, and [REPORT.md](REPORT.md) for the findings.
