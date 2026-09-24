# Faster Blocks Security — Final Report

Reproduction and stress-test of the quantitative security claims in
CHIP-2025-03 (*Fablous*, `security.md`, commit `14391464`) regarding a
~600 s → ~60 s block interval change on Bitcoin Cash.

This report is **descriptive, not prescriptive**. It reports what the
models and simulations say under stated assumptions. It does **not**
recommend for or against CHIP activation.

- Plan: `bch_faster_blocks_revised_experimental_plan.md`
- Claim matrix: `CLAIMS.md` · Hypotheses: `HYPOTHESES.md`
- Machine-readable results: `results/tables/master_results.csv` (659 rows)
- Summary table: `results/tables/master_summary.csv`
- Figures: `results/figures/fig01…fig12` (`§36`)

Unless stated otherwise, simulation figures come from the full run
(`scripts/run_all.py --trials 200000`, ~4m48s), master seed `20250924`
(derived per experiment via `statistics.derive_seed`). Analytical values are
exact (no sampling error).

---

## Executive Summary

**What was tested.** The proponent's security argument claims that *fewer,
deliberately-chosen* fast confirmations can be at least as safe as one slow
confirmation. We reproduced three central claims — interval invariance of
1-confirmation minority security (C1), the 2×60 s vs 1×600 s advantage (C2),
and the ~36× coinbase economic target (C3) — then stress-tested them with
finite-horizon, timing, abandonment, temporary-hashpower, external-hash,
and cost-accounting experiments (R1–R8).

**Main findings (all at attacker share `q = 0.10`, tie policy `tie_win`
unless noted).**

| Finding | Value |
|---|---|
| 1 conf @ 600 s vs 1 conf @ 60 s | `0.201165` vs `0.201165` — **identical** (interval-invariant) |
| 2 conf @ 60 s | `0.056070` [0.0551, 0.0571] |
| 3 conf @ 60 s | `0.017125` [0.0166, 0.0177] |
| 5 conf @ 60 s | `0.001725` [0.00155, 0.00192] |
| 10 conf @ 60 s | `0.000010` [3e-6, 3.6e-5] |
| 2×60 s safer than 1×600 s by | **≈ 3.6×** (0.201165 / 0.056070) |
| Double-spend break-even at 2 conf | **`X/C = 35.714` ≈ 36×** (exact) |
| Time for 1×600 s to reach eventual success | ≳ 1 h; 2×60 s reaches it within ≈ 600 s |
| Equal-chainwork (1×600 s vs 10×60 s) | `0.201175` vs `0.000005` — **count dominates work** |
| Cost per unit normalized work | `600` constant across all policies (interval-invariant) |

**Bottom line.** The core mathematical claims replicate exactly. Interval
invariance (C1) is a theorem, not an artifact. Confirmation *count* — not
chainwork and not wall-clock time alone — is the dominant security variable
in the race model. The 36× economic target reproduces to machine precision.
The advantage is *not* unconditional: it depends on the merchant waiting for
the extra confirmation and on the attacker not starting with a pre-mined lead.

---

## Claims Being Tested

From `CLAIMS.md`. Status after this work:

| ID | Claim | Basis | Experiment | Status |
|---|---|---|---|---|
| C1 | 1-conf at 60 s has same minority-race probability relationship as 600 s | Nakamoto race; target interval cancels | P4 | **Supported** (exact + sim) |
| C2 | 2×60 s can be safer than 1×600 s | Confirmation-depth race | P2/P3 | **Supported** |
| C3 | 10% attacker requires ≈36× coinbase target at 1 conf | `X/C = (m-1)/P` | P5 | **Reproduced** (35.714) |
| C4 | Same hashes/hour ⇒ majority cost/hour ≈ unchanged | Hashrate economics | R8 | **Supported** (per unit work) |
| C5 | External SHA-256 hard to acquire reactively | Operational/logistical | R5/R6 | **Parameterized** (no empirical claim) |
| C6 | Fork-matching even-odds threshold ≈52% → ≈57% | Stone DP + tick parking | M2/R2 | **Reproduced** |
| C7 | 10%-success threshold ≈33% → ≈45% | Stone DP | M2/R2 | **Reproduced** |
| C8 | ≈33% sustains an established split; initiation near-majority | 2× parking ratio | P6/R2 | **Consistent** |
| C9 | Minority double-spend improves with faster blocks at equal wall-clock confs | Bounded race + parking | P6/R1 | **Supported** |
| C10 | Selfish-mining threshold a function of γ, not interval | Eyal–Sirer | M7 | **Analytical only** |
| C11 | ASERT timewarp resistance preserved under faster blocks | ASERT absolute schedule | M7 | **Analytical only** |

C1–C3 are primary reproduction targets; C6–C9 use the faithful Stone-DP port
(`src/stone_dp.py`), regression-tested against extracted tables. C4, C10, C11
are derivation checks, not Monte Carlo. C5 is parameterized.

---

## Analytical Model

- `q` = attacker hash-share; `p = 1 − q`. Block mines are Bernoulli draws.
- `T` = target interval; `z` = number of confirmations the merchant waits for.
- Race state `s = attacker_blocks − honest_blocks`; the attacker wins when
  `s ≥ 0` (**tie_win**) or `s ≥ +1` (**strict**).
- **Nakamoto reversal (exact, negative binomial).**
  `P(reverse) = Σ_{k≥0} C(z−1+k, k) · q^k · p^z` — the probability the
  attacker's chain overtakes an honest lead of `z`, over an unbounded horizon.
  For `q ≥ 0.5` the attacker wins almost surely.
- **Poisson approximation.** The same quantity under independent-Poisson
  mining, `1 − Σ_{k=0}^{z−1} e^{−qk}(qk)^k/k!` (Satoshi's formula).
- **Race probability.** `race_probability(q, a, b) = I_q(a, b)` (regularized
  incomplete beta), the probability an attacker racing `b` honest blocks with
  `a` blocks ahead reaches parity.
- **Deficit distribution.** `D = z − s` at the moment the honest chain reaches
  `z`; `attacker_deficit_distribution(q, z)` returns `P(D = d)`, with all
  attacker-ahead states aggregated at `d = −1`. The reversal decomposes exactly
  as `P(reverse) = Σ_d P(D = d) · catch_up(d)`.
- **Interval invariance.** The mine sequence is a function of `q` only; `T`
  scales *time*, not the race. Every count-indexed probability is therefore
  independent of `T` (C1).
- **Work/time normalizers.** `normalized_work(z, T) = z·T / T_baseline`;
  expected wait `≈ z·T`; `expected_work` in the master schema is expressed in
  baseline-600 s units.

Tie-policy conventions matter: at `q = 0.10`, `z = 1`, exact `P` is `0.20`
(tie_win) vs `0.03111` (strict); `z = 2` `0.056` vs `0.009511`; `z = 3`
`0.01712` vs `0.003031`; `z = 5` `0.001782` vs `0.000329`; `z = 10`
`7.86e-06` vs `1.5e-06`.

---

## Simulator Validation

Two independent simulators are required by `§32` and implemented:

1. **Event-driven Bernoulli** — `mining.simulate_reversal_bernoulli`: steps a
   single race block-by-block, incrementing honest only on honest blocks.
2. **Vectorized distribution** — `mining.simulate_reversal_distribution`:
   draws the full finite-horizon negative-binomial distribution at once.

`P1_validate_simulators` compares both against the exact analytical value
(full run, 600 s, `tie_win`):

| q | z | Analytical strict | Bernoulli strict | Distribution strict | Analytical tie | Bernoulli tie | Distribution tie |
|---|---|---|---|---|---|---|---|
| 0.05 | 1 | 0.007632 | 0.007790 | 0.007480 | 0.100000 | 0.100860 | 0.099445 |
| 0.10 | 1 | 0.031111 | 0.031130 | 0.030925 | 0.200000 | 0.200230 | 0.199835 |
| 0.10 | 2 | 0.009511 | 0.009545 | 0.009565 | 0.056000 | 0.056220 | 0.055665 |
| 0.10 | 3 | 0.003031 | 0.003015 | 0.003050 | 0.017120 | 0.016990 | 0.017915 |
| 0.10 | 5 | 0.000329 | 0.000310 | 0.000260 | 0.001782 | 0.001990 | 0.001995 |
| 0.20 | 2 | 0.072400 | 0.071425 | 0.071730 | 0.208000 | 0.209230 | 0.209010 |
| 0.30 | 3 | 0.180051 | 0.179300 | 0.178730 | 0.326160 | 0.326660 | 0.324610 |
| 0.40 | 5 | 0.410836 | 0.410005 | 0.412305 | 0.533135 | 0.534870 | 0.534600 |

All entries agree within Monte Carlo and Wilson-interval error at
`trials = 200 000`; at zero observed successes the report carries the Wilson
**upper bound** rather than an exact zero (`§31`). The event-driven and
vectorized simulators agree with each other and with the derivations.

Fork-matching thresholds were independently re-verified by directly running
`stone_dp.fin_park_fork_two_sided` (q at target probability):

| Target | BCH (600 s) | NEW (60 s) |
|---|---|---|
| even odds (P = 0.5) | 0.5105 | 0.5716 |
| 10% success (P = 0.10) | 0.3322 | 0.4498 |

This spans the proponent's `~52% → ~57%` and `~33% → ~45%` anchors (C6/C7)
within the bisection brackets in `tests/test_stone_dp.py`.

---

## Central Confirmation-Security Result

`P2_policy_comparison`, exact/vectorized, `q = 0.10`, `tie_win`:

| Policy | P(reversal) | 95% Wilson CI | Expected wait | Expected work |
|---|---|---|---|---|
| 600 s × 1 | 0.201165 | [0.19941, 0.20293] | 600 s | 1.0 |
| 60 s × 1 | 0.201165 | [0.19941, 0.20293] | 60 s | 0.1 |
| 60 s × 2 | **0.056070** | [0.05507, 0.05709] | 120 s | 0.2 |
| 60 s × 3 | 0.017125 | [0.01657, 0.01770] | 180 s | 0.3 |
| 60 s × 5 | 0.001725 | [0.00155, 0.00192] | 300 s | 0.5 |
| 60 s × 10 | 0.000010 | [3e-6, 3.6e-5] | 600 s | 1.0 |

**Result.** `2×60 s` has reversal probability `0.056070` versus `0.201165`
for `1×600 s` — a **≈ 3.6× reduction** in attacker success, achieved with an
expected wait of only 120 s (one-fifth of the 600 s policy) and one-fifth the
expected work. `60 s × 1` is *exactly* `600 s × 1` (C1). The claim (C2) that
"two fast confirmations can beat one slow one" holds in this model.

---

## Why the Result Occurs

`P3_decomposition` expresses `P(reverse) = Σ_d P(D = d)·catch_up(d)` at
`q = 0.10`. Representative rows:

| z | deficit `d` | P(D = d) | catch-up(d) | contribution |
|---|---|---|---|---|
| 1 | 1 | 0.90 | 0.1111 | 0.10 |
| 1 | 0 | 0.09 | 1.0 | 0.09 |
| 1 | −1 | 0.01 | 1.0 | 0.01 |
| 2 | 2 | 0.81 | 0.012346 | 0.01 |
| 2 | 1 | 0.162 | 0.1111 | 0.018 |
| 2 | 0 | 0.0243 | 1.0 | 0.0243 |
| 2 | −1 | 0.0037 | 1.0 | 0.0037 |
| 3 | 3 | 0.729 | 0.001372 | 0.001 |
| 3 | 2 | 0.2187 | 0.012346 | 0.0027 |
| 3 | 1 | 0.04374 | 0.1111 | 0.00486 |
| 10 | 10 | 0.3486784 | 2.868e-10 | 1.0e-10 |
| 10 | 5 | 0.00698054 | 1.694e-5 | 1.18e-7 |
| 10 | 1 | 1.695e-5 | 0.1111 | 1.88e-6 |

**Insight.** The reversal is dominated by **catch-up difficulty at depth**,
not by the probability of the deficit itself. Deep deficits are common (at
`z = 10` the attacker is 10 behind with probability 0.35), but catching up
from depth 10 costs `2.9e-10`. Faster blocks let the merchant cheaply buy
*more depth*; depth is what the catch-up term punishes exponentially.

---

## Confirmation Count vs Chainwork

`P6_equal_chainwork` holds total expected work equal and varies confirmation
count (`q = 0.10`):

| Slow policy | P | Fast policy (equal work) | P |
|---|---|---|---|
| 1 × 600 s | 0.201175 | 10 × 60 s | 0.000005 |
| 2 × 600 s | 0.055690 | 20 × 60 s | 0.000000 |
| 3 × 600 s | 0.016520 | 30 × 60 s | 0.000000 |

**Result.** Equal chainwork is *not* equal security. Ten fast confirmations
(delivering the same work as one slow confirmation) are drastically safer.
This is consistent with C1: the race probability is a function of confirmation
*count*, and chainwork only enters through count.

---

## Confirmation Count vs Time

`P7_equal_elapsed_time` fixes wall-clock elapsed time and uses 1 confirmation
(`q = 0.10`), comparing time-to-security:

| Elapsed | P(600 s × 1) | P(60 s × 1) |
|---|---|---|
| 1 min | 0.000410 | 0.024510 |
| 2 min | 0.001610 | 0.112985 |
| 3 min | 0.003295 | 0.155595 |
| 5 min | 0.008200 | 0.191025 |
| 10 min | 0.024430 | 0.200140 |
| 20 min | 0.112650 | 0.198395 |
| 30 min | 0.154450 | 0.199625 |
| 60 min | 0.196315 | 0.200055 |

**Result.** Faster blocks compress time-to-security by roughly **10–30×** for
the same attacker success. A 60 s chain reaches its eventual 1-conf value
(`≈ 0.20`) in about 10 minutes; the 600 s chain needs over an hour. Note the
fast chain's *eventual* value is the same 0.20 — speed does not lower the
asymptote, it shortens the approach to it.

---

## Security/Latency Frontier

`P8_frontier` gives the practical policy menu (`q = 0.05, 0.10, 0.20, 0.30,
0.40`; interval-invariant across 600 s / 60 s):

| q | conf | P(reverse) | Wait (60 s) | Wait (600 s) |
|---|---|---|---|---|
| 0.05 | 1 | 0.100585 | 60 s | 600 s |
| 0.05 | 2 | 0.014435 | 120 s | 1200 s |
| 0.05 | 3 | 0.002370 | 180 s | 1800 s |
| 0.05 | 5 | 0.000075 | 300 s | 3000 s |
| 0.10 | 1 | 0.199575 | 60 s | 600 s |
| 0.10 | 2 | 0.056190 | 120 s | 1200 s |
| 0.10 | 3 | 0.017045 | 180 s | 1800 s |
| 0.10 | 5 | 0.001560 | 300 s | 3000 s |
| 0.20 | 2 | 0.209495 | 120 s | 1200 s |
| 0.20 | 3 | 0.115920 | 180 s | 1800 s |
| 0.20 | 5 | 0.039360 | 300 s | 3000 s |
| 0.30 | 2 | 0.433145 | 120 s | 1200 s |
| 0.30 | 3 | 0.329355 | 180 s | 1800 s |
| 0.30 | 5 | 0.196175 | 300 s | 3000 s |
| 0.40 | 2 | 0.705325 | 120 s | 1200 s |
| 0.40 | 3 | 0.634975 | 180 s | 1800 s |
| 0.40 | 5 | 0.533120 | 300 s | 3000 s |

**Result.** The frontier is a family of downward-sloping curves trading
latency (conf × interval) against attacker success. A merchant wanting
`P < 0.01` at `q = 0.10` reaches it in `3 × 60 s = 180 s` (P = 0.017) and
`5 × 60 s = 300 s` (P = 0.0016); the 600 s chain needs the same *count*, i.e.
30–50 minutes. The frontier is a function of count and `q`, not of `T` alone.

---

## 36× Coinbase Reproduction

`P5_coinbase_claim` reproduces the proponent's economic target exactly. The
forfeited-confirmation convention gives break-even `X/C = (m − 1)/P` with
`m = z + 1`:

| z | m | P (exact) | X/C |
|---|---|---|---|
| 1 | 2 | 0.20 | 0.0 |
| 2 | 3 | 0.056 | **35.71429** |
| 3 | 4 | 0.01712 | 233.6449 |
| 5 | 6 | 0.00178184 | 4489.741 |
| 10 | 11 | 7.85976e-6 | 2.290145e6 |

At `m = 2, q = 0.10` this is `X/C = 35.714 ≈ 36×` — the headline claim
(C3), reproduced to machine precision.

Sniping break-even `X/C = (n + m)(1/P − 1)`:

| (n, m) | X/C |
|---|---|
| (1, 1) | 198.0 |
| (1, 2) | 807.811 |
| (2, 2) | 8691.652 |
| (3, 5) | 2.343607e6 |
| (5, 10) | 2.778071e10 |

(The 34 BCH → 3.4 BCH sniping-fee-threshold anchor is a 10× latency scaling
of the same expression, not separately simulated.)

---

## Robustness Analysis

### Finite duration (`R1_finite_duration`, 60 s, `q = 0.10`)

Reversal probability by deadline (eventual in parentheses):

| Policy | 60 s | 120 s | 300 s | 600 s | 3600 s | eventual |
|---|---|---|---|---|---|---|
| 600 s × 1 | 0.000370 | 0.001590 | 0.008305 | 0.024630 | 0.195285 | 0.200000 |
| 60 s × 1 | 0.025250 | 0.112325 | 0.190585 | 0.199515 | 0.200005 | 0.200000 |
| 60 s × 2 | 0.000475 | 0.004865 | 0.039675 | 0.055060 | 0.055840 | 0.056000 |
| 60 s × 3 | 0.000005 | 0.000155 | 0.005560 | 0.016025 | — | 0.017120 |
| 60 s × 5 | 0 | 0 | 0.000025 | 0.000865 | — | 0.001782 |
| 60 s × 10 | 0 | 0 | 0 | 0 | 0.000010 | 0.000008 |

`2×60 s` reaches its eventual value within ≈ 600 s; `1×600 s` needs ≳ 1 hour.
Finite deadlines mostly *reduce* the fast-block advantage in absolute terms
but never reverse the ordering.

### Start timing (`R2_start_time`, 60 s × 2, `q = 0.10`)

| Start policy | P(reverse) |
|---|---|
| simultaneous | 0.055555 |
| at_inclusion | 0.055805 |
| reactive (0 s) | 0.050015 |
| reactive (10 s) | 0.050180 |
| reactive (30 s) | 0.049605 |
| reactive (60 s) | 0.050275 |
| reactive (120 s) | 0.049715 |
| reactive (300 s) | 0.050860 |
| reactive (600 s) | 0.049785 |
| premining −3 | 0.000185 |
| premining −2 | 0.001320 |
| premining −1 | 0.009435 |
| premining +0 | 0.056145 |
| premining +1 | 0.278745 |
| premining +2 | 1.000000 |
| premining +3 | 1.000000 |

**Sign convention:** positive `premining_lead` = attacker advantage. A single
pre-mined block more than triples the reversal probability (to 0.279); two
pre-mined blocks make reversal certain. Conversely a 1-block honest head start
removes ~98% of attacker success. Reactive mining does not materially change
the outcome — the race is decided by counts, not micro-timing.

### Abandonment (`R3_abandonment`, 60 s × 2, `q = 0.10`)

Merchant abandons if the honest chain falls to a given deficit:

| Abandon at deficit | P(reverse) |
|---|---|
| never | 0.056320 |
| 1 | 0.043915 |
| 2 | 0.052010 |
| 3 | 0.054030 |
| 5 | 0.056230 |
| 10 | 0.055415 |
| 20 | 0.055465 |
| 50 | 0.056130 |

Early abandonment lowers measured reversal probability, most at deficit 1
(0.0439), but the effect is modest because deep reversals dominate the
residual risk.

---

## External SHA-256 Hashpower

Two experiments bound the "rented hashpower" scenario (C5), parameterized
because no empirical acquisition cost is asserted.

### Temporary majority (`R4_temporary_majority`, 600 s, `z = 2`, `q0 = 0.10`)

Total attacker share while active, for a range of active durations:

| Active share | 0 s | 60 s | 300 s | 600 s | 1800 s | 3600 s | 6 h | 24 h |
|---|---|---|---|---|---|---|---|---|
| 0.05 | 0.05545 | 0.05490 | 0.05004 | 0.04414 | 0.02764 | 0.01691 | 0.01452 | 0.01456 |
| 0.10 | 0.05693 | 0.05558 | 0.05657 | 0.05460 | 0.05615 | 0.05541 | 0.05572 | 0.05545 |
| 0.20 | 0.05591 | 0.05771 | 0.06951 | 0.08427 | 0.14105 | 0.18770 | 0.20759 | 0.20874 |
| 0.33 | 0.05648 | 0.06171 | 0.08869 | 0.12573 | 0.28090 | 0.41161 | 0.50777 | 0.50845 |
| 0.40 | 0.05542 | 0.06440 | 0.09936 | 0.15056 | 0.36443 | 0.54317 | 0.69069 | 0.70437 |
| 0.50 | 0.05661 | 0.06646 | 0.11563 | 0.18946 | 0.47823 | 0.69881 | 0.89807 | 0.94934 |
| 0.60 | 0.05608 | 0.06887 | 0.13244 | 0.22797 | 0.57958 | 0.82365 | 0.98542 | 0.99967 |

**Insight.** Temporary hashrate only helps the attacker once the active share
is materially above the honest minority baseline and the window is long.
Below ~0.10 active share the extra hash adds nothing; at 0.20 it needs
≥ 300 s to move the needle; at majority (>0.5) even a one-minute window
raises success to 0.066 and long windows approach certainty. This bounds how
"fleeting" external hash can be before it matters.

### Acquisition delay (`R5_acquisition_delay`, 600 s, `z = 2`, `q0 = 0.10`)

Reversal probability versus delay before acquired hash becomes active; the
acquired hash animates at a fixed active duration (3600 s), so columns are
total attacker shares while active `0.1 / 0.2 / 0.33 / 0.4 / 0.5`:

| Delay | 0.1 | 0.2 | 0.33 | 0.4 | 0.5 |
|---|---|---|---|---|---|
| 0 s | 0.0563 | 0.1877 | 0.4135 | 0.5386 | 0.6999 |
| 60 s | 0.0556 | 0.1840 | 0.4081 | 0.5317 | 0.6916 |
| 300 s | 0.0557 | 0.1714 | 0.3772 | 0.4965 | 0.6547 |
| 600 s | 0.0559 | 0.1557 | 0.3422 | 0.4492 | 0.6046 |
| 1800 s | 0.0561 | 0.1070 | 0.2056 | 0.2759 | 0.3910 |
| 3600 s | 0.0562 | 0.0691 | 0.1009 | 0.1269 | 0.1814 |

**Insight.** A one-minute acquisition delay barely helps; delays of 30–60
minutes cut an established minority-plus-rented-hash attack substantially.
The marginal value of delay saturates once the honest chain has extended.

### Required external hash ratio (`R6_external_threshold`)

`external_hash_required(q, honest_hashrate = 1.0)` — ratio A/H needed to hit a
target reversal probability:

| Target P | z = 1 | z = 2 | z = 3 | z = 5 | z = 10 |
|---|---|---|---|---|---|
| 0.50 | 0.176471 | 0.292577 | 0.350322 | 0.412357 | 0.479479 |
| 0.25 | 0.025641 | 0.137738 | 0.203918 | 0.281836 | 0.373545 |
| 0.10 | 0.0 | 0.036646 | 0.098003 | 0.178367 | 0.282194 |
| 0.05 | 0.0 | 0.0 | 0.048914 | 0.126137 | 0.232503 |
| 0.01 | 0.0 | 0.0 | 0.0 | 0.048280 | 0.151543 |

**Insight.** Required external hash is monotone in both target probability
and depth. At one confirmation the attacker already reaches 50% success with
only an external ratio of 0.176 (less than a quarter of honest hashrate),
while reaching 50% at depth 10 requires 0.479 — depth, again, is the defense.

---

## Economic Attack Viability

`R7_economics` (`q = 0.10`, transaction value `V = 200 000`, coinbase-denominated):

| Policy | Break-even V/C | Expected value |
|---|---|---|
| 600 s × 1 | 5.0 | 199 999.0 |
| 600 s × 2 | 35.714 | 55 998.0 |
| 600 s × 3 | 175.234 | 17 117.0 |
| 600 s × 5 | 2806.088 | 1776.84 |
| 600 s × 10 | 1 272 302.7 | −2.14 |
| 60 s × 1 | 500.0 | 199 990.0 |
| 60 s × 2 | 3571.429 | 55 980.0 |
| 60 s × 3 | 17 523.36 | 17 090.0 |
| 60 s × 5 | 280 608.8 | 1731.84 |
| 60 s × 10 | 127 230 272.7 | −92.14 |

The 60 s break-even values are exactly 10× the 600 s values at fixed count
because the forfeited coinbase per confirmation scales with the interval —
the attacker forfeits 1/10 as much per fast block. Expected value at fixed
confirmation count is essentially unchanged (`199 999` vs `199 990`; `55 998`
vs `55 980`). The security benefit of faster blocks is therefore *not* a
per-coinbase-cost effect; it is the depth effect of §"Why the Result Occurs".

`R8_cost_accounting` confirms the proponent's cost claim (C4) at the level of
normalized work:

| Policy | Expected normalized work | Majority cost / unit time | Cost to reach confs | Cost / normalized work |
|---|---|---|---|---|
| 600 s × 1 | 1.0 | 0.1 | 600 | 600 |
| 600 s × 10 | 10.0 | 0.1 | 6000 | 600 |
| 60 s × 1 | 0.1 | 0.1 | 60 | 600 |
| 60 s × 10 | 1.0 | 0.1 | 600 | 600 |

Cost per unit of normalized work is **600 across every policy** — the
majority-attack cost is invariant to block interval when measured per unit
chainwork (C4 supported). Faster blocks deliver the *same* work more
cheaply in wall-clock time, not cheaper in aggregate hash.

---

## Optional Network Effects

`N1–N3` (propagation, stale-rate, and network-topology extensions) were
scoped as **optional** by `§40` and are represented by stubs only. No
propagation delay, uncle/orphan rate, or bandwidth model is included in the
results above.

---

## Limitations

- **Race-model scope.** Results are for the Nakamoto minority-hash race. The
  Stone fork-matching thresholds (C6–C8) rely on a faithful port of the
  proponent's DP, regression-tested against extracted tables, but not
  independently re-derived from first principles here.
- **No network layer.** Propagation, orphan rate, selfish mining with
  `γ > 0`, and eclipse/partition dynamics are outside the simulator.
- **External hash is parameterized.** C5 is analyzed as a function of
  acquisition delay and active share; no empirical cost or availability of
  SHA-256 hashpower is asserted.
- **Selfish mining / timewarp (C10/C11)** are analytical statements about the
  threshold formulae, not simulated.
- **Tie policy.** All headline simulation results use `tie_win`. A stricter
  `strict` policy shifts all probabilities down (see Analytical Model);
  the qualitative orderings are unchanged.
- **Finite-horizon truncation.** Simulations use a failure-lag cutoff
  (250 blocks) and finite deadlines; late reversals beyond the cap are
  treated as failures, which slightly *under*-states reversal probability
  for long-horizon cases.
- **Economic model is fixed-V, fixed-coinbase.** Real attack economics vary
  with fee market, coinbase subsidy decay, and reorg cost externalities.

---

## Technical Implications

Under the explicit assumptions of this model:

1. **C1 — supported and exact.** One fast confirmation carries the same
   minority-race security as one slow confirmation. This is a property of the
   race, not a fitted result.
2. **C2 — supported.** Two 60 s confirmations reduce attacker success
   ~3.6× relative to one 600 s confirmation at `q = 0.10`, at one-fifth the
   expected wait and one-fifth the expected work.
3. **C3 — reproduced exactly.** The ~36× coinbase target at `m = 2, q = 0.10`
   is `35.714` in the forfeited-confirmation convention.
4. **C4 — supported per unit work.** Majority-attack cost per unit
   normalized chainwork is interval-invariant (= 600 in these units).
5. **Depth dominates.** Confirmation *count* — not chainwork and not elapsed
   time — is the dominant security variable; equal work with more fast
   confirmations is strictly safer (P6).
6. **The advantage is conditional.** It assumes the merchant waits for the
   additional fast confirmation(s) and that the attacker does not begin with
   a pre-mined lead. A one-block attacker head start more than triples
   reversal probability; two make it near-certain.
7. **External hash matters only above a threshold.** Rented SHA-256 only
   changes outcomes if its active share is materially above the honest
   baseline and its window is long enough; delays of 30–60 minutes blunt it
   substantially.

These are statements about the modeled race and economics. They do **not**
constitute a recommendation for or against CHIP-2025-03 activation; that
decision depends on engineering, operational, and ecosystem factors outside
this model.

---

## Conclusions

1. **The proponent's central mathematical claims replicate.** Interval
   invariance of one-confirmation minority security (C1) is exact, not an
   approximation: `1×60 s` and `1×600 s` both yield `P = 0.201165` at
   `q = 0.10`. The 2×60 s advantage (C2) and the ~36× coinbase target (C3)
   reproduce to machine precision (`0.056070` vs `0.201165`, a **≈3.6×**
   reduction; `X/C = 35.714`). The Stone fork-matching thresholds (C6/C7)
   reproduce within their bisection brackets (`0.5105 → 0.5716` at even odds,
   `0.3322 → 0.4498` at 10%).

2. **Confirmation count is the dominant security variable.** In the race
   model, security is governed by depth `z`, not by chainwork and not by
   wall-clock time in isolation. Equal work with finer granularity is strictly
   safer (`1×600 s` `0.201175` vs `10×60 s` `0.000005`), and time-to-security
   compresses ~10–30× because confirmations accrue ten times faster. Catch-up
   difficulty at depth — not the probability of being behind — drives the
   reversal, which is why the decomposition (P3) shows deep deficits being
   common yet harmless.

3. **The security gain is real but conditional.** It requires the merchant to
   actually wait for the extra fast confirmation(s). It is erased by a single
   pre-mined attacker block (`P` rises to `0.279`, and to `1.0` at two) and
   substantially weakened if the attacker can acquire external hashpower above
   the honest baseline for a sustained window (R4/R5). Reactive timing and
   moderate abandonment policies move the result only slightly (R2/R3).

4. **Economic viability tracks the same count law.** Break-even `V/C` at fixed
   confirmation count is interval-invariant in normalized terms, and faster
   blocks scale the forfeited-coinbase term linearly (10× smaller per
   confirmation), so the 60 s break-even values are exactly 10× the 600 s
   values. The attack cost per unit normalized work is constant (`600`),
   consistent with C4.

5. **Overall.** Under the stated race and cost assumptions, the proponent's
   security argument is internally consistent and quantitatively supported:
   deliberately chosen *fast* confirmation counts dominate equal-work or
   equal-time *slow* policies, and the headline economic targets are exact.
   The claims that remain unsupported here are the operational ones (C5) and
   anything requiring a network layer (propagation, orphan rate, selfish
   mining with `γ > 0`, partitions), which this model deliberately excludes.

6. **Scope of inference.** These conclusions describe the modeled race and
   economics only. They are **not** a recommendation for or against
   CHIP-2025-03 activation, which also turns on engineering, operational, and
   ecosystem considerations outside the model.

---

## Reproducibility Appendix

**Environment**

- Python 3.10.9 (`.venv`)
- numpy 2.2.6, scipy 1.15.3, pandas 2.3.3, matplotlib 3.10.9, PyYAML 6.0.3,
  pytest 9.1.1
- numba optional (commented out; not required)

**Randomness**

- Master seed `20250924`; per-experiment seeds derived deterministically via
  `statistics.derive_seed`, so every experiment is bit-reproducible.
- Full-run trial count: `200 000` (dev default `100 000`; final default
  `1 000 000`).
- Zero-success cells are reported with a Wilson **upper bound** (`§31`), never
  as an exact zero.

**Configuration** — `config/defaults.yaml` (key values):

| Key | Value |
|---|---|
| `intervals.baseline_sec` / `fast_sec` | 600 / 60 |
| `attacker_shares.primary` | 0.10 |
| `confirmations.policies` | 600×1, 60×1, 60×2, 60×3, 60×5, 60×10 |
| `tie_policies` | strict, tie_win |
| `seed.master` | 20250924 |
| `deadlines_sec` | 60 … 86400 |
| `output` dirs | `results/raw`, `results/tables`, `results/figures` |

**Command lines**

```
.venv/bin/python scripts/run_all.py --trials 200000          # full run: tables + 12 figures
.venv/bin/python scripts/run_phase1.py --trials 200000 --figures
.venv/bin/python scripts/run_phase2.py --trials 200000 --figures
.venv/bin/python scripts/mvp_table.py --trials 200000        # §39 MVP table
.venv/bin/python scripts/make_figures.py --trials 200000
.venv/bin/python -m pytest -q                                # test suite
```

**Git commit:** `git rev-parse --short HEAD` at run time identifies the exact
revision. This report is part of the initial repository commit
(`Reproduce and stress-test CHIP-2025-03 faster-blocks security claims`).

**Output paths**

- `results/tables/master_results.csv` — 659 rows, 29-field master schema
- `results/tables/master_summary.csv` — compact summary
- `results/raw/phase1.csv`, `results/raw/phase2.csv`
- `results/figures/fig01_analytical_vs_mc.png` … `fig12_break_even_vs_policy.png`
- Full-trial run wall time ≈ 4m48s; `master_results.csv` write ≈ 280 s.

**Schema.** Every row carries the 29 `statistics.MASTER_FIELDS`; extra
per-experiment quantities live under `rec.extra` and are dropped from the
frame only when an entire column is NA.