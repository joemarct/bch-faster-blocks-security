"""Economic attack-viability model (plan section 25 / R7).

The core accounting is deliberately explicit so nothing is hidden in a
convention (plan section 25: "do not assume all private mining lost"):

    EV = P_success * (V + R_success) + (1 - P_success) * R_failure
         - C_hash - C_other - L_failure

where

* ``V``          -- double-spend / attack value (value extracted on success),
* ``P_success``  -- probability the attack succeeds (from the security model),
* ``R_success``  -- additional rewards collected on success (e.g. private-chain
                    coinbase that survives into the winning chain),
* ``R_failure``  -- rewards still collected on failure (usually 0, but a
                    profitable minority miner may keep orphan-side rewards),
* ``C_hash``     -- cost of the attacker's expected hashing work,
* ``C_other``    -- other costs (bandwidth, opportunity, operational),
* ``L_failure``  -- value lost when the attack fails (e.g. forfeited goods,
                    reputational or legal cost).

Break-even asks for the attack value ``V`` (or its multiple of a reference
coinbase ``C``) that makes ``EV = 0``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .analytical import (
    doublespend_break_even_multiple,
    race_probability,
    sniping_break_even_multiple,
)


# --------------------------------------------------------------------------
# Explicit EV ledger
# --------------------------------------------------------------------------
@dataclass
class EconomicModel:
    """Full economic model for one attack configuration.

    All monetary quantities share the same unit (e.g. BCH). ``cost_per_work``
    is the cost to produce one unit of block-work, so that
    ``C_hash = expected_attacker_blocks * cost_per_work`` and the same cost
    applies to any interval once work is normalised (plan section 26 / R8).
    """

    double_spend_value: float
    reference_coinbase: float
    attacker_share: float
    success_probability: float
    expected_attacker_blocks: float
    cost_per_work: float = 1.0
    success_reward: float = 0.0
    failure_reward: float = 0.0
    other_costs: float = 0.0
    failure_loss: float = 0.0
    extra: dict[str, Any] = field(default_factory=dict)

    # -- component ledgers ---------------------------------------------------
    def hashing_cost(self) -> float:
        return self.expected_attacker_blocks * self.cost_per_work

    def components(self) -> dict[str, float]:
        """Itemised accounting, guaranteed to sum to :meth:`expected_value`."""
        p = self.success_probability
        return {
            "success_gross": p * (self.double_spend_value + self.success_reward),
            "failure_gross": (1.0 - p) * self.failure_reward,
            "hashing_cost": self.hashing_cost(),
            "other_costs": self.other_costs,
            "failure_loss": self.failure_loss,
        }

    def expected_value(self) -> float:
        c = self.components()
        return (
            c["success_gross"]
            + c["failure_gross"]
            - c["hashing_cost"]
            - c["other_costs"]
            - c["failure_loss"]
        )

    def break_even_value(self) -> float:
        """Attack value ``V`` at which ``EV = 0`` (inf if never profitable)."""
        p = self.success_probability
        if p <= 0.0:
            return float("inf")
        cost = self.hashing_cost() + self.other_costs + self.failure_loss
        other_rev = p * self.success_reward + (1.0 - p) * self.failure_reward
        return (cost - other_rev) / p

    def break_even_multiple(self) -> float:
        """``V / C`` at break-even (zero/negative -> attacker already favoured)."""
        if self.reference_coinbase <= 0.0:
            raise ValueError("reference_coinbase must be positive")
        return self.break_even_value() / self.reference_coinbase

    def profitable(self) -> bool:
        return self.expected_value() > 0.0


# --------------------------------------------------------------------------
# Convenience constructors
# --------------------------------------------------------------------------
def attack_value_multiple(
    q: float,
    z: int,
    success_probability: float,
    expected_attacker_blocks: float,
    baseline_interval_sec: float = 600.0,
    interval_sec: float = 600.0,
    coinbase_per_work: float = 1.0,
    other_costs: float = 0.0,
    failure_loss: float = 0.0,
    success_reward: float = 0.0,
    failure_reward: float = 0.0,
) -> EconomicModel:
    """Build an :class:`EconomicModel` with the coinbase as the value unit.

    Work is normalised so that one *baseline* block's work costs
    ``coinbase_per_work``; a fast block costs ``interval/baseline`` of that
    (plan sections 5.1-5.2, 26). Setting ``reference_coinbase`` to the
    per-block reward (in the same unit) makes :meth:`break_even_multiple`
    directly comparable to the Fablous "36x coinbase" claim.
    """
    work_per_block = interval_sec / baseline_interval_sec
    cost_per_work = coinbase_per_work / work_per_block if work_per_block else 0.0
    # Reference coinbase: reward actually earned per (fast) block produced.
    ref_coinbase = coinbase_per_work * work_per_block
    return EconomicModel(
        double_spend_value=0.0,
        reference_coinbase=ref_coinbase,
        attacker_share=q,
        success_probability=success_probability,
        expected_attacker_blocks=expected_attacker_blocks,
        cost_per_work=cost_per_work,
        success_reward=success_reward,
        failure_reward=failure_reward,
        other_costs=other_costs,
        failure_loss=failure_loss,
        extra={"z": z},
    )


# --------------------------------------------------------------------------
# Analytic break-even reproductions (Fablous / Stone)
# --------------------------------------------------------------------------
def doublespend_break_even_table(
    q: float, confirmations: list[int]
) -> dict[int, float]:
    """``V/C = (m - 1) / I_q(m, m)`` for each recipient requirement ``m``.

    Fablous convention: ``m`` is the confirmation count entering ``I_q(m, m)``;
    the recipient waits ``m - 1`` confirmations. At ``q = 0.10`` and ``m = 2``
    (one confirmation) this yields the headline ``~36x`` (36 = 35.714).
    """
    return {m: doublespend_break_even_multiple(q, m) for m in confirmations}


def sniping_break_even_table(
    q: float, n_m_pairs: list[tuple[int, int]]
) -> dict[tuple[int, int], float]:
    """``V/C = (n + m) * (1 / I_q(n + m, m) - 1)`` for sniping races.

    ``n`` = blocks the attacker is behind, ``m`` = attacker blocks needed.
    """
    return {nm: sniping_break_even_multiple(q, nm[0], nm[1]) for nm in n_m_pairs}


# --------------------------------------------------------------------------
# Cost accounting across intervals (plan section 26 / R8)
# --------------------------------------------------------------------------
def hashrate_cost_per_second(
    attacker_share: float, total_hashrate: float, cost_per_hash_sec: float
) -> float:
    """Cost per wall-clock second of running the attacker's share.

    Identical for both intervals at fixed ``q``: the security benefit of fast
    blocks is not a cost discount (plan section 26).
    """
    return attacker_share * total_hashrate * cost_per_hash_sec


def cost_per_confirmation(
    confirmations: int, interval_sec: float, total_hashrate: float, cost_per_hash_sec: float
) -> float:
    """Cost to *reach* a given confirmation depth at nominal cadence."""
    return confirmations * interval_sec * total_hashrate * cost_per_hash_sec


def cost_per_successful_reversal(
    success_probability: float,
    expected_attack_duration_sec: float,
    total_hashrate: float,
    cost_per_hash_sec: float,
) -> float:
    """Expected cost per *successful* reversal (``inf`` if success impossible)."""
    if success_probability <= 0.0:
        return float("inf")
    return (
        total_hashrate * expected_attack_duration_sec * cost_per_hash_sec
        / success_probability
    )


# --------------------------------------------------------------------------
# Sniping EV shortcut (Fablous formulation)
# --------------------------------------------------------------------------
def sniping_attack_value(
    q: float, n: int, m: int, coinbase: float, reachable_value: float
) -> float:
    """EV of a sniping attempt on a mempool-visible prize.

    ``P = I_q(n + m, m)``; the attacker mines ``m`` private blocks (cost
    ``m * coinbase`` if coinbase is the per-block cost/reward unit) to overtake
    ``n`` blocks. Positive EV means the prize is worth sniping.
    """
    p = race_probability(q, n + m, m)
    return p * reachable_value - m * coinbase
