# Revised Experimental Plan: Independent Reproduction and Robustness Testing of Faster-Block Confirmation Security

## 1. Purpose

This project will independently reproduce and then stress-test the
quantitative security claims relevant to reducing the Bitcoin Cash (BCH)
target block interval from approximately 600 seconds to approximately 60
seconds under CHIP-2025-03 ("Faster Blocks").

The project is **not** intended to begin from the assumption that either
10-minute or 1-minute blocks are preferable. Its purpose is narrower and
more scientific:

> **First reproduce the claimed security advantage of finer confirmation
> granularity under the proponent's own stated assumptions. Then
> systematically relax those assumptions and determine where the
> conclusion continues to hold.**

The most important claim to reproduce is:

> Against a persistent minority-hash attacker, two 1-minute
> confirmations can be more secure than one 10-minute confirmation,
> despite representing only about one fifth as much expected accumulated
> proof of work.

A second concrete claim to investigate is:

> For a 10% attacker, a one-confirmation double-spend target must be
> approximately 36 times the coinbase/block reward to break even.

The project should distinguish mathematical consequences of a model from
empirical facts about the BCH network. It should also distinguish:

-   work per block;
-   cumulative chainwork;
-   confirmation depth;
-   elapsed wall-clock time;
-   probability of reversal;
-   finite-horizon attack probability;
-   economic profitability;
-   practical availability of external SHA-256 hashrate.

The requested implementation language is Python.

Preferred libraries:

-   NumPy
-   SciPy
-   Pandas
-   Matplotlib
-   Optional: Numba
-   Optional: multiprocessing or concurrent.futures

All experiments must be reproducible from fixed random seeds,
parameterized centrally, and capable of exporting machine-readable
results.

------------------------------------------------------------------------

# 2. Why This Revision Exists

The Fablous/CHIP material already contains quantitative analysis of
several effects associated with faster blocks, including topics such as
block propagation, stale/orphan rates, mining dynamics, header-chain
growth, SPV implications, and activation costs.

The proposal and related discussion also contain a theoretical argument
that **confirmation count and cumulative chainwork are distinct security
dimensions**.

Therefore, this project should not spend its initial effort duplicating
all of those analyses.

The apparent gap worth investigating first is narrower:

> There should be an independently reproducible numerical demonstration
> of the minority-attacker confirmation-security claim, followed by
> sensitivity analysis showing exactly which assumptions make that
> result true.

The project should therefore proceed in two major phases.

## Phase I --- Reproduction

Reproduce the security claims under the standard assumptions used by the
proponent/Nakamoto-style minority-attacker model.

## Phase II --- Robustness

Relax those assumptions one at a time and determine whether the
conclusions survive.

Only after these phases should optional network-level extensions such as
propagation and stale-block modeling be considered.

------------------------------------------------------------------------

# 3. Core Research Questions

## RQ1 --- Reproduction of the central claim

Under a standard persistent-minority-attacker Poisson/Nakamoto model,
is:

\[ P\_{`\mathrm{reverse}`{=tex}}(60s,2,q) \<
P\_{`\mathrm{reverse}`{=tex}}(600s,1,q) \]

for relevant values of:

\[ q \< 0.5? \]

In particular, verify this for:

\[ q = 0.10. \]

## RQ2 --- Why does the result occur?

If two 1-minute confirmations outperform one 10-minute confirmation
under the model despite much less expected accumulated PoW, identify
mathematically which feature of the model produces that result.

Do not merely report probabilities.

Explain the mechanism.

## RQ3 --- What role does target interval itself play?

Determine precisely when changing the target interval:

\[ T=600s `\rightarrow `{=tex}60s \]

changes modeled reversal probability and when it merely rescales
wall-clock time.

## RQ4 --- Confirmation count versus chainwork

At approximately equal expected cumulative chainwork, do different
confirmation counts produce different minority-attacker reversal
probabilities?

Example:

\[ 1`\times`{=tex}600s \]

versus:

\[ 10`\times`{=tex}60s. \]

If so, explain why.

## RQ5 --- Confirmation count versus elapsed time

How does the result change when security is conditioned on elapsed
wall-clock time instead of a fixed number of confirmations?

## RQ6 --- Economic claim

Can the claimed approximately 36× coinbase break-even target for a 10%
attacker be reproduced?

Under exactly which assumptions?

## RQ7 --- Robustness to attacker assumptions

Does the central result survive when the attacker:

-   has a finite attack duration;
-   uses rational abandonment;
-   starts at a different time;
-   acquires external SHA-256 hashrate after a delay;
-   temporarily becomes a majority attacker;
-   faces explicit economic costs?

------------------------------------------------------------------------

# 4. Claim Matrix

Before implementing simulations, create a structured claim matrix.

Suggested schema:

  ----------------------------------------------------------------------------------------------------------------------
  Claim ID Claim           Source/Context   Model Basis              Derivation   Numerical   Empirical     Experiment
                                                                     Present?     Example     Evidence      
                                                                                  Present?    Present?      
  -------- --------------- ---------------- ------------------------ ------------ ----------- ------------- ------------
  C1       1-conf at 60s   Proponent        Nakamoto race            TBD          TBD         No direct BCH P1
           has same        argument                                                           experiment    
           minority-race                                                                      identified    
           probability                                                                                      
           relationship as                                                                                  
           1-conf at 600s                                                                                   

  C2       2×60s           Proponent        Confirmation-depth race  TBD          Asserted    No direct     P2
           confirmations   argument                                                           simulation    
           can be safer                                                                       identified    
           than 1×600s                                                                                      

  C3       10% attacker    Proponent        Attack economics         TBD          Yes         Not           P5
           requires \~36×  argument                                                           identified    
           coinbase target                                                                                  

  C4       Same            Proponent        Hashrate economics       Conceptual   Partial     Requires      R4
           hashes/hour     argument                                                           assumptions   
           means majority                                                                                   
           attack                                                                                           
           cost/hour is                                                                                     
           approximately                                                                                    
           unchanged                                                                                        

  C5       External        Proponent        Operational/logistical   No           No          TBD           R5/R6
           SHA-256         argument                                                                         
           capacity is                                                                                      
           operationally                                                                                    
           difficult to                                                                                     
           acquire                                                                                          
           reactively                                                                                       
  ----------------------------------------------------------------------------------------------------------------------

The coding/research agent should update this matrix after inspecting the
actual CHIP and associated source material.

Do not mark a claim as unsupported merely because it lacks a simulation.
A mathematical derivation is valid support if the assumptions and
derivation are correct.

------------------------------------------------------------------------

# 5. Terminology and Security Metrics

The project must keep the following concepts separate.

## 5.1 Work per block

Normalize current expected block work as:

\[ W\_{600}=1.0. \]

With unchanged total hashrate:

\[ W\_{60}=0.1. \]

This normalization is for comparison only.

## 5.2 Cumulative chainwork

Total work accumulated by a chain.

Under fixed normalized difficulty:

\[ W\_{`\mathrm{chain}`{=tex}} = nW\_{`\mathrm{block}`{=tex}}. \]

## 5.3 Confirmation depth

Use the merchant-facing convention:

> A transaction has one confirmation when it is included in one block.

Thus:

-   `z = 1`: transaction is included in the current tip;
-   `z = 2`: one additional block has been built on top;
-   etc.

Document this convention everywhere.

## 5.4 Reversal probability

Probability that the attacker's competing chain satisfies the specified
success condition.

Run at least two tie policies:

### Tie policy A

Attacker success requires strictly greater cumulative chainwork.

### Tie policy B

Reaching equal cumulative chainwork counts as success.

The main report should explain which assumption best corresponds to the
analytical formula being reproduced.

## 5.5 Eventual reversal probability

Probability of eventual success if the attacker can continue
indefinitely.

## 5.6 Finite-horizon reversal probability

Probability of success before a deadline:

\[ P(`\mathrm{success\ before}`{=tex} D). \]

## 5.7 Economic attack viability

Expected profitability after accounting for:

-   attack success probability;
-   hash cost/opportunity cost;
-   mining rewards;
-   transaction value;
-   failure losses;
-   abandonment strategy.

Do not use "security" as a synonym for all of these simultaneously.

------------------------------------------------------------------------

# 6. Baseline Mathematical Model

Let:

\[ q = `\text{attacker fraction of total effective hashrate}`{=tex} \]

and:

\[ p = 1-q. \]

For target interval:

\[ T, \]

aggregate block arrival rate is:

\[ `\lambda=1`{=tex}/T. \]

Model honest and attacker mining as independent Poisson processes:

\[ `\lambda`{=tex}\_h=p/T \]

and:

\[ `\lambda`{=tex}\_a=q/T. \]

Equivalent waiting times:

\[ X_h`\sim`{=tex}`\mathrm{Exp}`{=tex}(`\lambda`{=tex}\_h) \]

\[ X_a`\sim`{=tex}`\mathrm{Exp}`{=tex}(`\lambda`{=tex}\_a). \]

The event-driven simulator should explicitly sample these processes.

------------------------------------------------------------------------

# 7. Key Mathematical Observation to Verify

If both honest and attacker rates are multiplied by the same factor,
then the probability that the next block is found by the attacker
remains:

\[ `\frac{\lambda_a}{\lambda_a+\lambda_h}`{=tex}=q. \]

Therefore changing:

\[ T=600s \]

to:

\[ T=60s \]

may simply compress the same stochastic block race into one tenth the
wall-clock time under a stationary fixed-share model.

This should **not** be assumed as the conclusion.

It should be:

1.  derived analytically;
2.  reproduced numerically;
3.  tested against alternative attacker models.

One major objective of the project is to identify exactly where this
invariance breaks.

------------------------------------------------------------------------

# 8. Attacker Fractions

Baseline sweep:

``` text
q = [
    0.01,
    0.05,
    0.10,
    0.15,
    0.20,
    0.25,
    0.30,
    0.35,
    0.40,
    0.45,
    0.49
]
```

Use denser sampling around regions where results change rapidly.

Majority scenarios must be modeled separately.

------------------------------------------------------------------------

# PHASE I --- INDEPENDENT REPRODUCTION

# 9. P0 --- Analytical Baseline

Before running Monte Carlo simulations, implement the relevant
analytical formulas.

At minimum implement:

## 9.1 Catch-up probability from a known deficit

For a minority attacker starting `d` blocks/work units behind, implement
the appropriate gambler's-ruin/catch-up expression under clearly stated
assumptions.

The familiar simplified expression involves:

\[ (q/p)\^d \]

for:

\[ q\<p, \]

but the exact formula depends on the success boundary.

## 9.2 Nakamoto Section 11 model

Implement the whitepaper-style calculation in which:

1.  the honest network accumulates `z` confirmations;
2.  the attacker mines privately during this time;
3.  the number of attacker blocks found during the honest confirmation
    period is modeled probabilistically;
4.  the attacker then attempts to catch up from the resulting deficit.

Document the derivation.

Do not merely paste a formula.

## Deliverable

Create:

``` text
src/analytical.py
```

with tested functions such as:

``` python
catchup_probability(q, deficit, tie_policy)
nakamoto_reversal_probability(q, z, tie_policy)
```

------------------------------------------------------------------------

# 10. P1 --- Validate Monte Carlo Against Analytical Results

This is mandatory before interpreting any experiment.

## Simulator A --- Event-driven

Explicitly sample exponential waiting times for honest and attacker
blocks.

## Simulator B --- Distribution-based

Use mathematically equivalent direct sampling from
Poisson/negative-binomial distributions where appropriate.

The two simulators should be implemented independently enough that one
is not simply a wrapper around the other.

## Procedure

For each:

``` text
q = 0.05, 0.10, 0.20, 0.30, 0.40
```

and:

``` text
z = 1, 2, 3, 5, 10
```

compare:

-   analytical probability;
-   event-driven Monte Carlo;
-   vectorized/distribution Monte Carlo.

## Trials

Development:

``` text
100,000 per cell
```

Final important cells:

``` text
1,000,000+ per cell
```

Use larger samples or analytical methods for rare events.

## Acceptance condition

Monte Carlo should agree with the analytical result within statistical
sampling uncertainty.

If not, stop and resolve the mismatch.

------------------------------------------------------------------------

# 11. P2 --- Directly Test the 2×60s vs 1×600s Claim

This is the highest-priority experiment.

For every selected `q`, compare:

``` text
600s × 1 confirmation

60s × 1 confirmation
60s × 2 confirmations
60s × 3 confirmations
60s × 4 confirmations
60s × 5 confirmations
60s × 10 confirmations
```

For each policy report:

-   expected merchant wait;
-   simulated mean wait;
-   median wait;
-   waiting-time percentiles;
-   expected normalized chainwork at acceptance;
-   mean realized chainwork;
-   attacker's private-chain state distribution at acceptance;
-   eventual reversal probability;
-   finite-horizon reversal probabilities;
-   95% confidence interval.

## Primary q = 0.10 table

The report must prominently contain:

  -----------------------------------------------------------------------
  Policy       Expected Wait  Expected Work       Reversal         95% CI
                                               Probability 
  ----------- -------------- -------------- -------------- --------------
  600s × 1            \~600s            1.0         result         result

  60s × 1              \~60s            0.1         result         result

  60s × 2             \~120s            0.2         result         result

  60s × 3             \~180s            0.3         result         result

  60s × 5             \~300s            0.5         result         result

  60s × 10            \~600s            1.0         result         result
  -----------------------------------------------------------------------

This table should be one of the central outputs of the entire project.

------------------------------------------------------------------------

# 12. P3 --- Explain the Result, Not Just Measure It

If:

\[ P(60s,2)\<P(600s,1), \]

despite:

\[ W(60s,2)`\approx`{=tex}0.2W(600s,1), \]

the report must explain why.

Investigate:

-   attacker block distribution while the honest chain accumulates
    confirmations;
-   deficit distribution at merchant acceptance;
-   probability of attacker already being tied/ahead;
-   conditional catch-up probability from each deficit;
-   effect of requiring multiple honest block discoveries.

For each acceptance policy, output the distribution:

``` text
attacker deficit at acceptance
```

for example:

``` text
attacker ahead
tie
1 behind
2 behind
3 behind
...
```

Then decompose total reversal probability as:

\[ P(`\mathrm{reverse}`{=tex}) = `\sum`{=tex}\_d P(D=d)
P(`\mathrm{catchup}`{=tex}`\mid `{=tex}D=d). \]

This decomposition is extremely important.

It should reveal exactly where the confirmation-count effect arises.

------------------------------------------------------------------------

# 13. P4 --- Fixed Confirmation Count, Different Block Interval

Compare:

\[ P(T=600,z,q) \]

against:

\[ P(T=60,z,q) \]

for identical `z` and `q`.

Run:

``` text
z = 1, 2, 3, 5, 10
```

If the stationary model predicts equality, verify it numerically.

This should establish whether target interval itself appears in reversal
probability under the baseline assumptions or merely rescales time.

------------------------------------------------------------------------

# 14. P5 --- Reproduce the \~36× Coinbase Claim

Treat this as a standalone reproduction target.

## Target claim

A 10% attacker allegedly needs a double-spend target of approximately 36
times the coinbase/block reward to break even at one confirmation.

## Required work

Determine the exact economic model that produces this figure.

Explicitly model:

-   attacker hash fraction;
-   mining cost;
-   attack duration;
-   private-chain mining rewards;
-   rewards if attack succeeds;
-   rewards if attack fails;
-   value of the double-spend;
-   abandonment strategy;
-   tie handling.

Attempt:

1.  analytical reproduction;
2.  independent simulation reproduction.

If 36× is not reproduced, identify which assumptions produce the
discrepancy.

Do not tune the model merely to force 36×.

------------------------------------------------------------------------

# 15. P6 --- Equal Expected Chainwork

Compare approximately equal expected work:

``` text
600s × 1 conf  vs  60s × 10 conf
600s × 2 conf  vs  60s × 20 conf
600s × 3 conf  vs  60s × 30 conf
```

Measure reversal probability.

If probabilities differ despite equal expected work, decompose why.

This directly tests whether:

> "same expected cumulative PoW"

and:

> "same modeled minority-attacker security"

are equivalent statements.

------------------------------------------------------------------------

# 16. P7 --- Equal Elapsed Time

Now condition on wall-clock time rather than confirmation count.

Time horizons:

``` text
60 sec
120 sec
180 sec
300 sec
600 sec
900 sec
1200 sec
1800 sec
3600 sec
```

For each horizon and network:

1.  simulate honest and attacker mining for exactly the specified time;
2.  record block counts;
3.  record cumulative work;
4.  record relative chain state;
5.  optionally continue the attack afterward to estimate eventual
    reversal.

Do not assume exactly ten 60-second blocks occur in 600 seconds.

Preserve the Poisson distribution.

------------------------------------------------------------------------

# 17. P8 --- Security/Latency Frontier

For each `q`, construct a security/latency frontier.

## X-axis

Acceptance latency.

Use both:

-   expected latency;
-   simulated median latency.

## Y-axis

Reversal probability.

Plot:

-   600-second confirmation policies;
-   60-second confirmation policies.

Questions:

-   At equal expected latency, which policy gives lower modeled reversal
    probability?
-   At equal reversal probability, which policy gives lower latency?
-   Does one policy dominate under the stationary minority-attacker
    model?
-   If so, what assumption creates that dominance?

This should be one of the principal figures.

------------------------------------------------------------------------

# PHASE II --- ROBUSTNESS TESTING

# 18. Purpose of Phase II

Phase I asks:

> Is the proponent's claim correct under the stated Nakamoto-style
> assumptions?

Phase II asks:

> How robust is that conclusion when those assumptions are relaxed?

Every Phase II experiment must explicitly identify which baseline
assumption it changes.

------------------------------------------------------------------------

# 19. R1 --- Finite Attack Duration

Baseline Nakamoto-style calculations often concern eventual catch-up.

Real attacks have finite time and budgets.

Test deadlines:

``` text
1 minute
2 minutes
5 minutes
10 minutes
30 minutes
1 hour
6 hours
24 hours
```

Calculate:

\[ P(`\mathrm{success\ before}`{=tex} D). \]

Compare with eventual success probability.

Report how the ranking of confirmation policies changes, if at all.

------------------------------------------------------------------------

# 20. R2 --- Attacker Start-Time Sensitivity

Run several start policies.

## A. Simultaneous start

Attacker begins mining the conflicting chain when the transaction is
broadcast.

## B. Start at transaction inclusion

Attacker begins only after the merchant transaction enters a block.

## C. Reactive start with delay

Attacker begins after observing a trigger.

Delays:

``` text
0 sec
10 sec
30 sec
60 sec
120 sec
300 sec
600 sec
```

## D. Pre-mining/private lead

Allow initial private-chain states:

``` text
-3
-2
-1
0
+1
+2
+3
```

Define sign convention explicitly.

This experiment should reveal how sensitive the confirmation advantage
is to attack timing.

------------------------------------------------------------------------

# 21. R3 --- Rational Attack Abandonment

Implement attacker strategies.

## Strategy A

Never abandon within a very large cutoff.

## Strategy B

Abandon when deficit reaches:

``` text
1
2
3
5
10
20
50
```

## Strategy C

Abandon after fixed time.

## Strategy D

Abandon when expected future value becomes negative.

Compare:

-   success probability;
-   expected attack duration;
-   expected cost;
-   expected profit.

This converts the theoretical infinite-horizon race into a more
economically meaningful model.

------------------------------------------------------------------------

# 22. R4 --- Temporary Majority Hashpower

Model a time-varying attacker share:

\[ q(t)=q_0 \]

normally, then:

\[ q(t)=q_a \]

during an attack window.

Test:

``` text
q0 = 0.01, 0.05, 0.10
```

Temporary shares:

``` text
qa = 0.30
qa = 0.40
qa = 0.49
qa = 0.51
qa = 0.60
qa = 0.75
qa = 0.90
```

Durations:

``` text
60 sec
120 sec
300 sec
600 sec
1800 sec
3600 sec
7200 sec
```

For `qa > 0.5`, unlimited-duration eventual success is not the
interesting metric.

Measure:

-   success before hash expires;
-   time to success;
-   required initial deficit;
-   attack cost.

------------------------------------------------------------------------

# 23. R5 --- Delayed Acquisition of External SHA-256 Hashrate

This is particularly relevant to the BCH security discussion.

Do not assume external SHA-256 capacity is:

-   instantly available; or
-   impossible to obtain.

Parameterize it.

Acquisition delays:

``` text
0 sec
30 sec
60 sec
120 sec
300 sec
600 sec
1800 sec
3600 sec
```

Temporary attacker shares:

``` text
0.30
0.40
0.49
0.51
0.60
0.75
0.90
```

Availability durations:

``` text
60 sec
120 sec
300 sec
600 sec
1800 sec
3600 sec
7200 sec
```

Compare 60-second and 600-second confirmation policies.

## Required heatmaps

For each selected attack duration:

-   x-axis: external-hash acquisition delay;
-   y-axis: attacker share after acquisition;
-   cell: success probability.

Produce equivalent figures for both block intervals.

------------------------------------------------------------------------

# 24. R6 --- External Hash Threshold Analysis

Instead of choosing arbitrary temporary attacker shares only, calculate:

> What additional hashrate would be required to reach each effective
> `q`?

Use normalized BCH honest hashrate first.

Example:

If honest BCH hashrate is normalized to `H = 1`, determine the external
attacker hashrate `A` needed for:

\[ q=`\frac{A}{A+H}`{=tex}. \]

Thus:

\[ A=`\frac{q}{1-q}`{=tex}H. \]

Report normalized requirements.

Optionally add real BCH/BTC hashrate data only if fresh, sourced
measurements are deliberately introduced.

Keep sourced empirical data separate from the abstract model.

------------------------------------------------------------------------

# 25. R7 --- Economic Attack Model

Define:

-   `V` = double-spend value;
-   `P_success` = attack success probability;
-   `C_hash` = hash acquisition/opportunity cost;
-   `C_other` = additional costs;
-   `R_success` = mining rewards retained on success;
-   `R_failure` = mining rewards retained on failure;
-   `L_failure` = other failure losses.

A generic expected-value framework:

\[ EV = P_s(V+R_s) + (1-P_s)R_f - C\_{`\mathrm{hash}`{=tex}} -
C\_{`\mathrm{other}`{=tex}} - L\_{`\mathrm{failure}`{=tex}}. \]

Do not assume all private mining expenditure is lost.

Model canonical/non-canonical reward outcomes explicitly.

Use block-reward multiples before introducing fiat prices.

Target values:

``` text
0.1× reward
0.5×
1×
2×
5×
10×
20×
36×
50×
100×
500×
1000×
```

Calculate break-even values for each acceptance policy.

------------------------------------------------------------------------

# 26. R8 --- Majority Attack Cost per Unit Time

Independently test the argument:

> Because the network purchases approximately the same number of hashes
> per hour, sustaining majority hashrate for an hour should cost
> approximately the same regardless of whether blocks target 60 or 600
> seconds.

Model:

-   same total honest hashes/sec;
-   same attacker hashes/sec;
-   different difficulty/work per block.

Verify:

-   cost per second;
-   expected blocks produced;
-   expected work;
-   success time distribution.

Then distinguish:

-   cost per hour;
-   cost per confirmation attack;
-   cost per successful reversal.

These are not necessarily identical metrics.

------------------------------------------------------------------------

# PHASE III --- OPTIONAL NETWORK-LEVEL EXTENSIONS

# 27. Why These Are Secondary

Fablous already contains quantitative treatment of propagation,
stale/orphan rates, mining effects, SPV/header growth, and related
activation considerations.

Therefore these experiments are useful primarily as:

-   independent reproduction;
-   sensitivity analysis;
-   integration with the attack model.

They should not delay Phase I.

------------------------------------------------------------------------

# 28. N1 --- Propagation Delay

Introduce propagation delay distributions.

Start with hypothetical values:

``` text
100 ms
500 ms
1 sec
2 sec
5 sec
10 sec
```

Use:

-   fixed delays;
-   log-normal delays;
-   optional empirical distributions if sourced data become available.

Measure:

-   stale rate;
-   honest effective chain-growth rate;
-   accidental forks;
-   attacker advantage.

Clearly label hypothetical parameters.

------------------------------------------------------------------------

# 29. N2 --- Stale/Orphan Effects

Allow honest miners to temporarily mine on different tips.

Compare:

-   600-second blocks;
-   60-second blocks.

Measure whether increased stale rates materially change the baseline
security/latency frontier.

This experiment should attempt to connect network propagation effects
with the minority-attacker model rather than merely duplicate stale-rate
estimates.

------------------------------------------------------------------------

# 30. N3 --- Miner Heterogeneity

Optional advanced model:

-   miners with different hash shares;
-   different propagation latencies;
-   topology effects;
-   pool concentration.

Measure whether faster blocks disproportionately advantage
well-connected miners and whether that affects attack security.

This is outside the minimum viable project.

------------------------------------------------------------------------

# 31. Statistical Standards

All Monte Carlo estimates must include uncertainty.

For binary outcomes:

\[ `\hat `{=tex}p=k/n. \]

Report 95% confidence intervals.

Prefer Wilson intervals.

For zero observed successes, never report exact zero probability.

Report an upper confidence bound.

For very rare events, use:

-   analytical formulas;
-   importance sampling;
-   variance reduction;
-   or substantially larger trial counts.

Document the method.

------------------------------------------------------------------------

# 32. Simulation Implementation

Use two baseline implementations.

## Event-driven reference simulator

Explicit exponential waiting times.

Purpose:

-   conceptual transparency;
-   time-varying hashpower;
-   finite deadlines;
-   external-hash scenarios.

## Vectorized simulator

Use NumPy/SciPy distributions.

Purpose:

-   large Monte Carlo runs;
-   parameter sweeps;
-   independent reproduction.

Optional Numba acceleration is acceptable after correctness is
established.

------------------------------------------------------------------------

# 33. Suggested Project Structure

``` text
bch-faster-blocks-security/
│
├── README.md
├── CLAIMS.md
├── requirements.txt
├── pyproject.toml
│
├── config/
│   └── defaults.yaml
│
├── notebooks/
│   ├── 01_analytical_baseline.ipynb
│   ├── 02_validate_simulators.ipynb
│   ├── 03_core_claim.ipynb
│   ├── 04_chainwork_vs_confirmations.ipynb
│   ├── 05_equal_time.ipynb
│   ├── 06_security_latency.ipynb
│   ├── 07_36x_claim.ipynb
│   ├── 08_finite_attacks.ipynb
│   ├── 09_external_hash.ipynb
│   └── 10_economics.ipynb
│
├── src/
│   ├── __init__.py
│   ├── analytical.py
│   ├── mining.py
│   ├── attacks.py
│   ├── external_hash.py
│   ├── economics.py
│   ├── statistics.py
│   ├── experiments.py
│   └── plotting.py
│
├── tests/
│   ├── test_analytical.py
│   ├── test_event_simulator.py
│   ├── test_vectorized_simulator.py
│   ├── test_analytical_vs_simulation.py
│   ├── test_chainwork.py
│   ├── test_economics.py
│   └── test_reproducibility.py
│
├── results/
│   ├── raw/
│   ├── tables/
│   └── figures/
│
└── scripts/
    ├── run_phase1.py
    ├── run_robustness.py
    ├── run_external_hash.py
    └── run_economics.py
```

------------------------------------------------------------------------

# 34. Required Unit Tests

At minimum:

1.  `q = 0` cannot reverse a confirmed honest chain.
2.  Majority attacker approaches success probability 1 with unlimited
    time.
3.  Increasing confirmation depth does not increase minority-attacker
    eventual reversal probability under identical assumptions.
4.  Analytical and Monte Carlo results agree.
5.  Event-driven and vectorized simulators agree.
6.  Under stationary fixed-share assumptions, changing `T` while
    preserving `q` behaves according to the analytical prediction.
7.  Wall-clock waiting distributions change appropriately with `T`.
8.  Cumulative work normalization is correct.
9.  Finite-horizon success is never greater than unlimited-horizon
    success.
10. Same seed reproduces results.
11. Independent seeds produce statistically compatible estimates.
12. Temporary hashpower activates/deactivates at the configured times.
13. Economic accounting conserves modeled rewards/costs.

------------------------------------------------------------------------

# 35. Pre-Registered Hypotheses

Record these before examining final results.

## H1

Under the stationary fixed-share minority-attacker model, absolute
target interval does not materially affect reversal probability at fixed
confirmation depth; it primarily rescales wall-clock time.

## H2

Under that model:

\[ P(60s,2,q)\<P(600s,1,q) \]

for minority `q`, because the two policies differ in confirmation depth
even though the former has less expected chainwork.

## H3

At equal expected cumulative chainwork, a larger number of confirmations
may produce a different minority-attacker reversal probability than
fewer heavier blocks.

## H4

The explanation for H2/H3 can be decomposed through the attacker's
deficit distribution at merchant acceptance and conditional catch-up
probabilities.

## H5

Conditioning on elapsed time instead of confirmation count changes the
framing of the comparison.

## H6

Time-varying external SHA-256 hashrate makes absolute wall-clock time
relevant in ways absent from the stationary model.

## H7

Finite attack duration and rational abandonment materially alter
economic attack viability relative to infinite-horizon catch-up
probability.

## H8

The \~36× coinbase claim is reproducible only under a specific set of
economic assumptions that should be made explicit.

These are hypotheses, not desired conclusions.

------------------------------------------------------------------------

# 36. Required Figures

## Figure 1

Analytical versus Monte Carlo reversal probability.

## Figure 2

Reversal probability versus confirmation depth.

## Figure 3

Focused comparison:

``` text
600s × 1
60s × 1
60s × 2
60s × 3
60s × 5
60s × 10
```

## Figure 4

Attacker deficit distribution at acceptance.

## Figure 5

Reversal probability decomposition by deficit.

## Figure 6

Equal expected chainwork comparison.

## Figure 7

Reversal probability versus elapsed time.

## Figure 8

Security/latency frontier.

## Figure 9

Finite attack duration curves.

## Figure 10

Temporary-majority duration heatmap.

## Figure 11

External-hash acquisition-delay heatmap.

## Figure 12

Break-even transaction value versus confirmation policy.

------------------------------------------------------------------------

# 37. Master Results Schema

Use a machine-readable table with fields such as:

``` text
experiment
phase
model
target_interval_sec
attacker_share
confirmations
acceptance_policy
expected_wait_sec
mean_wait_sec
median_wait_sec
expected_work
mean_realized_work
attack_start_policy
initial_attacker_state
external_hash_share
external_hash_delay_sec
external_hash_duration_sec
attack_deadline_sec
abandonment_policy
tie_policy
trials
successes
success_probability
ci_lower
ci_upper
mean_attack_duration_sec
expected_attack_cost
break_even_value_reward_multiple
seed
code_version
```

------------------------------------------------------------------------

# 38. Interpretation Rules

## Rule 1

If the proponent's central claim is reproduced, say so explicitly.

Example:

> Under the standard persistent-minority Nakamoto race model, the
> simulation and analytical calculation confirm that two 1-minute
> confirmations have a lower reversal probability than one 10-minute
> confirmation.

Then immediately state the assumptions.

## Rule 2

Do not turn a model-specific result into a universal statement.

Avoid:

> Two 1-minute confirmations are simply more secure than one 10-minute
> confirmation.

unless every relevant security dimension has actually been established.

## Rule 3

If target interval cancels out mathematically under a model, explain
why.

## Rule 4

If conclusions change under temporary external hashpower, identify the
exact parameter region.

## Rule 5

Distinguish simulation evidence from empirical network evidence.

Monte Carlo validates consequences of assumptions.

It does not establish that those assumptions describe real attackers.

## Rule 6

Do not treat historical operation of Litecoin, Dogecoin, Zcash, or other
chains as controlled proof of BCH security.

Such evidence can be contextual but is not a substitute for the modeled
comparison.

------------------------------------------------------------------------

# 39. Minimum Viable Research Result

Before doing any advanced experiments, the project must produce one
independently verified table for:

\[ q=0.10. \]

Required policies:

``` text
600s × 1 confirmation
60s × 1 confirmation
60s × 2 confirmations
60s × 3 confirmations
60s × 5 confirmations
60s × 10 confirmations
```

Required columns:

``` text
policy
expected_wait
median_wait
expected_normalized_work
analytical_reversal_probability
simulated_reversal_probability
95% confidence interval
mean attacker deficit at acceptance
finite_10min_success_probability
finite_1h_success_probability
```

If this table is correct and independently reproducible, the project has
already answered the most immediate dispute.

------------------------------------------------------------------------

# 40. Recommended Execution Order

Execute in this exact order:

``` text
1. Build claim matrix
2. Implement analytical model
3. Implement scalar event simulator
4. Implement vectorized simulator
5. Validate both simulators
6. Reproduce 2×60s vs 1×600s claim
7. Decompose why the result occurs
8. Reproduce ~36× coinbase claim
9. Compare equal chainwork
10. Compare equal elapsed time
11. Build security/latency frontier
12. Add finite attack durations
13. Add start-time sensitivity
14. Add rational abandonment
15. Add temporary external SHA-256 hash
16. Add economic model
17. Only then consider propagation/stale extensions
```

Do not jump directly to complicated network simulation before the
baseline mathematics are reproduced.

------------------------------------------------------------------------

# 41. Final Report

The final research report should contain:

## Executive Summary

What was tested and the main numerical findings.

## Claims Being Tested

The completed claim matrix.

## Analytical Model

Definitions and derivations.

## Simulator Validation

Analytical versus numerical agreement.

## Central Confirmation-Security Result

The 2×60s versus 1×600s comparison.

## Why the Result Occurs

Deficit-distribution decomposition.

## Confirmation Count vs Chainwork

Equal-work analysis.

## Confirmation Count vs Time

Equal-time analysis.

## Security/Latency Frontier

Practical policy comparison.

## 36× Coinbase Reproduction

Economic derivation and simulation.

## Robustness Analysis

Finite duration, start timing, abandonment.

## External SHA-256 Hashpower

Temporary/delayed hash scenarios.

## Economic Attack Viability

Break-even analysis.

## Optional Network Effects

Propagation/stale extensions if completed.

## Limitations

What remains unmodeled.

## Technical Implications

State which security claims are supported under which assumptions.

Do not automatically turn the technical result into a recommendation for
or against CHIP activation.

## Reproducibility Appendix

Include:

-   package versions;
-   Python version;
-   random seeds;
-   configuration;
-   command lines;
-   git commit;
-   output paths.

------------------------------------------------------------------------

# 42. Scientific Standard

The strongest possible result is not one that "proves" either side
correct.

The strongest result is one that can say something like:

> Under assumptions A, B, and C, the proponent's claim is mathematically
> and numerically correct. When assumption B is replaced by B′, the
> result changes in the following measurable way.

That identifies the actual source of disagreement.

The project should therefore favor:

-   explicit assumptions;
-   independent implementations;
-   analytical cross-checks;
-   reproducibility;
-   sensitivity analysis;
-   transparent uncertainty;
-   parameter sweeps;
-   falsifiable claims.

The code and outputs should make it possible for a proponent or skeptic
to change a parameter, rerun the experiment, and see exactly why the
result changes.

------------------------------------------------------------------------

# 43. Primary Research Principle

The project should be guided by this sequence:

> **Reproduce first. Explain second. Stress-test third. Generalize only
> as far as the evidence permits.**

That sequence is especially important here because the central dispute
may not be about arithmetic at all. It may ultimately be about which
attacker model is most relevant to Bitcoin Cash.

The experiment should make that distinction visible.
