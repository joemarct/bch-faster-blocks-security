# Claim Matrix

Structured register of the quantitative claims under test. Populated before
final experiments and updated as evidence accumulates. A claim is **not**
marked unsupported merely for lacking a simulation; a correct mathematical
derivation with explicit assumptions counts as support.

Sources:
- **Fablous / CHIP-2025-03**: `gitlab.com/0353F40E/fablous`, `security.md`,
  commit `14391464`. Referenced as *Proponent*.
- **Stone (2020)**: "Attacks Against Auto-finalization and Fork Parking",
  re-implemented in `extras/stone/stone_all_attacks.py`.

## Reproduction anchors (extracted from `security.md`)

| Quantity | Proponent value | Where |
|---|---|---|
| Double-spend overtake, pre-parking | `P = I_q(m, m)` (m = conf + 1) | §"Double-Spend" table |
| Double-spend break-even (forfeited-conf convention) | `X/C = (m-1)/P` | same |
| **36× target** | `X/C = 36` at `m=2, q=0.10` | same, row m=2 |
| Parked-tip double-spend | `P = I_q(2m, m)` for `m > 4` (10-min) | parked table |
| Sniping overtake | `P = I_q(n+m, m)`; `X/C = (n+m)(1/P - 1)` | §"Sniping" |
| Sniping recovery | `X/C = (l+k-3)/P - (l+k+3)` | same |
| Sniping fee threshold | 34 BCH → 3.4 BCH with 1-min blocks | same |
| Fork-matching even-odds threshold | **~52% → ~57%** | §"Parking Chain Split" |
| Fork-matching 10%-success threshold | **~33% → ~45%** | same |
| Fork-matching crossing | near **0.60** hashpower | same |
| P(lock-in) at 50:50 | `0.5^3 = 12.5%` → `0.5^9 ≈ 0.2%` | same |
| Parking tiers (maintenance floors) | 50% / 44% / 40% / 33% | same |
| Tick parking schedule | `<600:0.5; 600–1799:300/tpb; 1800–2399:600/tpb; >=2400:m/2` | `stone_all_attacks.py` |
| Selfish mining threshold | `q > (1-γ)/(3-2γ)`; γ=0→33.3%, 1/2→25%, 1→0% | §"Selfish Mining" |
| Orphan cost | 0.41–1.94% | same |
| Timewarp (ASERT τ=172800s) | MTP +1.45% → +0.14%; FTL −2.85% | §"Timewarp" |
| Partition split-hashpower times | 10:90→388/526 min; 33:67→119/176; 49:51→81/121 | §"Network Partitions" |

## Matrix

| Claim ID | Claim | Source | Model basis | Derivation present? | Numerical example? | Empirical evidence? | Experiment |
|---|---|---|---|---|---|---|---|
| C1 | 1-conf at 60s has the same minority-race probability relationship as 1-conf at 600s | Proponent | Nakamoto race | Yes — target interval cancels (`λ_a/(λ_a+λ_h)=q`) | Yes | No direct BCH experiment identified | P4 |
| C2 | 2×60s confirmations can be safer than 1×600s | Proponent | Confirmation-depth race | Yes — finite-horizon NB/Poisson; depth effect | Asserted | No direct simulation identified | P2/P3 |
| C3 | 10% attacker requires ~36× coinbase target at 1 conf | Proponent | Attack economics, `X/C=(m-1)/P` | Yes | Yes (36 at m=2, q=0.10) | Not identified | P5 |
| C4 | Same hashes/hour ⇒ majority attack cost/hour ~unchanged | Proponent | Hashrate economics | Conceptual | Partial | Requires assumptions | R8 |
| C5 | External SHA-256 capacity is operationally hard to acquire reactively | Proponent | Operational/logistical | No | No | TBD | R5/R6 |
| C6 | Fork-matching even-odds threshold rises ~52%→~57% with faster blocks | Proponent (Stone reimpl.) | Stone fork-matching DP + tick parking | Yes | Yes (`fork_attack_plot.png`) | No | M2/R2 |
| C7 | 10%-success threshold rises ~33%→~45% | Proponent (Stone reimpl.) | same | Yes | Yes | No | M2/R2 |
| C8 | ~33% sustains an established split; initiation still near-majority | Proponent | 2× parking ratio + initiation race | Yes | Yes | No | P6/R2 |
| C9 | Minority double-spend security improves with faster blocks at equal wall-clock confirmations | Proponent | Bounded race + parking | Yes | Yes (`double_spend_plot_*`) | No | P6/R1 |
| C10 | Selfish-mining threshold is a function of γ, not target interval | Proponent | Eyal–Sirer | Yes | Yes | No | M7 (analytical) |
| C11 | ASERT timewarp resistance is preserved under faster blocks | Proponent | ASERT absolute schedule | Yes | Yes | No | M7 (analytical) |

## Status

- C1–C3: primary reproduction targets (Phase I, MVP).
- C6–C9: Fablous Stone-DP reproduction via faithful port (`src/stone_dp.py`),
  regression-tested against the extracted tables before any extension.
- C4, C10, C11: analytical/derivation checks, not Monte Carlo.
- C5: parameterized (R5/R6); no empirical claim asserted.