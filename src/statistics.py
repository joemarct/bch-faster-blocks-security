"""Statistical utilities: confidence intervals, seeds, result records.

All Monte Carlo estimates must include uncertainty (plan section 31).
Binary outcomes use Wilson score intervals; zero-success cells report an
upper confidence bound rather than an exact zero.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

try:  # scipy is a declared dependency; import defensively for clarity
    from scipy import stats as _scipy_stats
except Exception:  # pragma: no cover
    _scipy_stats = None


# --------------------------------------------------------------------------
# Confidence intervals
# --------------------------------------------------------------------------
def wilson_interval(
    successes: int, trials: int, confidence: float = 0.95
) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion.

    Well behaved for small counts and proportions near 0 or 1, unlike the
    normal approximation.
    """
    if trials <= 0:
        raise ValueError("trials must be positive")
    if not (0 <= successes <= trials):
        raise ValueError("successes must be in [0, trials]")
    if _scipy_stats is None:  # pragma: no cover
        raise RuntimeError("scipy is required for Wilson intervals")
    z = float(_scipy_stats.norm.ppf(1.0 - (1.0 - confidence) / 2.0))
    n = float(trials)
    phat = successes / n
    denom = 1.0 + z * z / n
    centre = phat + z * z / (2.0 * n)
    margin = z * math.sqrt(phat * (1.0 - phat) / n + z * z / (4.0 * n * n))
    lo = (centre - margin) / denom
    hi = (centre + margin) / denom
    return (max(0.0, lo), min(1.0, hi))


def wilson_upper_bound(successes: int, trials: int, confidence: float = 0.95) -> float:
    """One-sided upper confidence bound (used when zero successes observed)."""
    return wilson_interval(successes, trials, confidence)[1]


# --------------------------------------------------------------------------
# Deterministic seed management
# --------------------------------------------------------------------------
def derive_seed(master: int, *labels: Any) -> int:
    """Deterministically derive a 64-bit seed from a master seed and labels.

    Reproducible across processes and platforms: hashlib is unaffected by
    PYTHONHASHSEED (unlike the built-in ``hash()``).
    """
    digest = hashlib.sha256()
    digest.update(str(int(master)).encode("utf-8"))
    for label in labels:
        digest.update(b"\x1f")
        digest.update(str(label).encode("utf-8"))
    return int.from_bytes(digest.digest()[:8], "big", signed=False)


def make_rng(master: int, *labels: Any) -> np.random.Generator:
    """Return a NumPy Generator seeded deterministically from the labels."""
    return np.random.default_rng(derive_seed(master, *labels))


# --------------------------------------------------------------------------
# Result records / master schema (plan section 37)
# --------------------------------------------------------------------------
MASTER_FIELDS: tuple[str, ...] = (
    "experiment",
    "phase",
    "model",
    "target_interval_sec",
    "attacker_share",
    "confirmations",
    "acceptance_policy",
    "expected_wait_sec",
    "mean_wait_sec",
    "median_wait_sec",
    "expected_work",
    "mean_realized_work",
    "attack_start_policy",
    "initial_attacker_state",
    "external_hash_share",
    "external_hash_delay_sec",
    "external_hash_duration_sec",
    "attack_deadline_sec",
    "abandonment_policy",
    "tie_policy",
    "trials",
    "successes",
    "success_probability",
    "ci_lower",
    "ci_upper",
    "mean_attack_duration_sec",
    "expected_attack_cost",
    "break_even_value_reward_multiple",
    "seed",
    "code_version",
)


@dataclass
class ResultRecord:
    """A single machine-readable experiment result row.

    Fields not present in :data:`MASTER_FIELDS` are collected in ``extra``
    and flattened on serialisation, so experiments can carry diagnostics
    without schema churn.
    """

    experiment: str = ""
    phase: str = ""
    model: str = ""
    target_interval_sec: float | None = None
    attacker_share: float | None = None
    confirmations: int | None = None
    acceptance_policy: str = ""
    expected_wait_sec: float | None = None
    mean_wait_sec: float | None = None
    median_wait_sec: float | None = None
    expected_work: float | None = None
    mean_realized_work: float | None = None
    attack_start_policy: str = ""
    initial_attacker_state: int | None = None
    external_hash_share: float | None = None
    external_hash_delay_sec: float | None = None
    external_hash_duration_sec: float | None = None
    attack_deadline_sec: float | None = None
    abandonment_policy: str = ""
    tie_policy: str = ""
    trials: int | None = None
    successes: int | None = None
    success_probability: float | None = None
    ci_lower: float | None = None
    ci_upper: float | None = None
    mean_attack_duration_sec: float | None = None
    expected_attack_cost: float | None = None
    break_even_value_reward_multiple: float | None = None
    seed: int | None = None
    code_version: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    def set_ci(self, successes: int, trials: int, confidence: float = 0.95) -> "ResultRecord":
        """Populate success probability and Wilson CI from raw counts."""
        self.successes = int(successes)
        self.trials = int(trials)
        self.success_probability = successes / trials if trials else None
        lo, hi = wilson_interval(successes, trials, confidence)
        self.ci_lower, self.ci_upper = lo, hi
        return self

    def as_row(self) -> dict[str, Any]:
        """Flatten to a dict with MASTER_FIELDS first, then extras."""
        row: dict[str, Any] = {}
        for f in fields(self):
            if f.name == "extra":
                continue
            row[f.name] = getattr(self, f.name)
        for key, value in self.extra.items():
            if key in row:
                raise ValueError(f"extra key collides with master field: {key}")
            row[key] = value
        return row


def records_to_frame(records: list[ResultRecord]) -> pd.DataFrame:
    """Convert result records to a DataFrame with a stable column order."""
    rows = [r.as_row() for r in records]
    frame = pd.DataFrame(rows)
    ordered = [c for c in MASTER_FIELDS if c in frame.columns]
    ordered += [c for c in frame.columns if c not in ordered]
    return frame[ordered]


def write_master(frame: pd.DataFrame, path: str | Path) -> Path:
    """Append-safe CSV writer for the master results table.

    Writes atomically to ``path``; if the file exists, keeps a union of
    columns so heterogeneous experiments accumulate cleanly.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        existing = pd.read_csv(path)
        combined = pd.concat([existing, frame], ignore_index=True, sort=False)
    else:
        combined = frame
    tmp = path.with_suffix(path.suffix + ".tmp")
    combined.to_csv(tmp, index=False)
    tmp.replace(path)
    return path


def code_version(repo_root: str | Path | None = None) -> str:
    """Best-effort git revision string for the reproducibility appendix."""
    import subprocess

    root = Path(repo_root) if repo_root is not None else Path(__file__).resolve().parents[1]
    try:
        out = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        rev = out.stdout.strip()
        if out.returncode == 0 and rev:
            return rev
    except Exception:
        pass
    return "unknown"