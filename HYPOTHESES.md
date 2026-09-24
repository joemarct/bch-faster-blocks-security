# Pre-Registered Hypotheses

Recorded **before** examining final results (plan section 35). These are
hypotheses, not desired conclusions.

## H1 — Interval invariance
Under the stationary fixed-share minority-attacker model, the absolute target
interval does not materially affect reversal probability at fixed confirmation
depth; it primarily rescales wall-clock time.
*Rationale:* both rates scale by `1/T`, so the next-block originator is the
attacker with probability `q` independent of `T`; the race is self-similar.
*Status:* pending.

## H2 — Depth beats raw chainwork
Under that model, `P_reverse(60s, 2, q) < P_reverse(600s, 1, q)` for minority
`q`, because the two policies differ in confirmation depth even though the
former has ~1/5 the expected chainwork.
*Status:* pending.

## H3 — Confirmation count vs chainwork
At equal expected cumulative chainwork, a larger number of confirmations may
produce a different minority-attacker reversal probability than fewer heavier
blocks.
*Status:* pending.

## H4 — Decomposition
The explanation for H2/H3 can be decomposed through the attacker's deficit
distribution at merchant acceptance and the conditional catch-up probability,
`P_reverse = Σ_d P(D=d) P(catchup | D=d)`.
*Status:* pending.

## H5 — Time conditioning
Conditioning on elapsed time instead of confirmation count changes the framing
of the comparison.
*Status:* pending.

## H6 — Time-varying hashpower
Time-varying external SHA-256 hashrate makes absolute wall-clock time relevant
in ways absent from the stationary model.
*Status:* pending.

## H7 — Finite duration / abandonment
Finite attack duration and rational abandonment materially alter economic
attack viability relative to infinite-horizon catch-up probability.
*Status:* pending.

## H8 — 36× reproducibility
The ~36× coinbase claim is reproducible only under a specific, explicit set of
economic assumptions (notably: forfeited-confirmations convention, tie handling,
and treating the attack as unbounded in time).
*Status:* pending.