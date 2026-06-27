"""Sweep one memory parameter across a list of values and score recall (Iteration 5).

The experiment driver. Given a base ``MemoryConfig``, ONE parameter name, and a list
of values, it builds a variant config per value (changing only that field — ADR-002,
ADR-003), runs the full fixed probe set, scores recall, and records recall + latency.
A **no-memory baseline** (ADR-007) is always included as the control, and each config
can be **repeated N times and averaged** to tame LLM nondeterminism (ADR-008).

Long-term, not short-term — the thing that makes the baseline meaningful: each probe
seeds the fact on one agent (session A), flushes, waits out async extraction, then asks
on a FRESH agent (session B, *same actor*). The seed is therefore gone from short-term,
so only long-term memory can recall it — which is exactly what the swept params
(``top_k``, ``relevance_score``) affect. (Same-session would let short-term answer even
the no-memory baseline, collapsing the control — so we never do that here.)

Agent construction is INJECTED (an ``agent_builder`` callable) so the whole module is
offline-testable with fakes; the CLI in ``run.py`` injects the real Bedrock-backed
builder. The flush + extraction-lag lifecycle lives here, not in ``probes.run_probe``,
which stays a single deterministic pass.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, replace
from statistics import fmean
from typing import Any, Callable, Sequence

from agent.config import MemoryConfig
from memory.factory import close_session_manager
from probes import Probe, load_probes, run_probe

# Given a MemoryConfig, build an agent for it (its own session). The returned object is
# callable as ``agent(prompt) -> reply`` and exposes ``.memory_session_manager``.
AgentBuilder = Callable[[MemoryConfig], Any]

# The MemoryConfig fields we can sweep, each mapped to the type its raw value coerces to.
# Strategy and namespace are infra-level (a Terraform resource / a fixed scheme), not
# swept here; the short-term conversation window isn't wired into MemoryConfig yet.
SWEEPABLE: dict[str, Callable[[str], Any]] = {
    "top_k": int,
    "relevance_score": float,
    "batch_size": int,
}


@dataclass(frozen=True)
class SweepRow:
    """One row of the result table: a config label and how it scored."""

    label: str
    recall: float           # fraction of probes recalled, averaged over repeats (0..1)
    mean_latency_ms: float  # mean question-turn latency over all probes x repeats
    repeats: int
    n_probes: int


class _NoOpSeed:
    """A stand-in 'seed agent' that swallows the seed turn.

    The cross-session runner seeds the fact itself (so it can flush + wait before
    asking), then reuses ``run_probe`` only for the timed+scored question turn — this
    no-op absorbs ``run_probe``'s seed call so it isn't planted a second time.
    """

    def __call__(self, _prompt: str) -> None:
        return None


def build_variant_config(base: MemoryConfig, param: str, value: Any) -> MemoryConfig:
    """Return a copy of ``base`` with exactly ``param`` changed to ``value`` (memory on).

    Coerces the raw value to the field's type and relies on ``MemoryConfig.__post_init__``
    to reject out-of-range values. Only ``param`` (and ``enabled=True``) changes — every
    other field is inherited, so exactly one parameter varies (ADR-003).
    """
    if param not in SWEEPABLE:
        raise ValueError(f"unknown sweep param {param!r}; sweepable: {sorted(SWEEPABLE)}")
    coerced = SWEEPABLE[param](value)
    return replace(base, enabled=True, **{param: coerced})


def _run_probe_cross_session(
    probe: Probe,
    mem_cfg: MemoryConfig,
    build_agent: AgentBuilder,
    *,
    settle_seconds: float,
) -> Any:
    """Seed on one session, ask on a fresh session (same actor) — the long-term path."""
    seed_cfg = replace(mem_cfg, session_id=f"sweep-seed-{uuid.uuid4().hex[:8]}")
    seed_agent = build_agent(seed_cfg)
    try:
        seed_agent(probe.seed)
    finally:
        close_session_manager(getattr(seed_agent, "memory_session_manager", None))  # flush

    if settle_seconds:
        time.sleep(settle_seconds)  # let async fact extraction catch up (live only)

    question_cfg = replace(mem_cfg, session_id=f"sweep-ask-{uuid.uuid4().hex[:8]}")
    question_agent = build_agent(question_cfg)
    try:
        return run_probe(probe, seed_agent=_NoOpSeed(), question_agent=question_agent)
    finally:
        close_session_manager(getattr(question_agent, "memory_session_manager", None))


def run_config(
    label: str,
    mem_cfg: MemoryConfig,
    build_agent: AgentBuilder,
    probes: Sequence[Probe],
    *,
    repeats: int,
    settle_seconds: float,
) -> SweepRow:
    """Run the full probe set ``repeats`` times for one config; average recall + latency."""
    recall_per_repeat: list[float] = []
    latencies: list[float] = []
    for _ in range(repeats):
        correct = 0
        for probe in probes:
            result = _run_probe_cross_session(probe, mem_cfg, build_agent, settle_seconds=settle_seconds)
            correct += int(result.correct)
            latencies.append(result.latency_ms)
        recall_per_repeat.append(correct / len(probes))
    return SweepRow(
        label=label,
        recall=fmean(recall_per_repeat),
        mean_latency_ms=fmean(latencies) if latencies else 0.0,
        repeats=repeats,
        n_probes=len(probes),
    )


def run_sweep(
    param: str,
    values: Sequence[Any],
    base_mem_cfg: MemoryConfig,
    build_agent: AgentBuilder,
    *,
    probes: Sequence[Probe] | None = None,
    repeats: int = 1,
    settle_seconds: float = 0.0,
) -> list[SweepRow]:
    """Sweep ``param`` over ``values``; return the baseline row first, then one per value.

    Exactly one parameter varies across the value rows (ADR-003); the baseline disables
    memory entirely (ADR-007) as the floor every value is read against.
    """
    if param not in SWEEPABLE:
        raise ValueError(f"unknown sweep param {param!r}; sweepable: {sorted(SWEEPABLE)}")
    if repeats < 1:
        raise ValueError("repeats must be >= 1")
    probes = probes if probes is not None else load_probes()

    rows: list[SweepRow] = []
    # Baseline first (ADR-007): memory OFF, the control every value is compared against.
    baseline_cfg = replace(base_mem_cfg, enabled=False)
    rows.append(run_config("baseline (memory OFF)", baseline_cfg, build_agent, probes,
                           repeats=repeats, settle_seconds=settle_seconds))
    for value in values:
        variant = build_variant_config(base_mem_cfg, param, value)
        label = f"{param}={getattr(variant, param)}"
        rows.append(run_config(label, variant, build_agent, probes,
                               repeats=repeats, settle_seconds=settle_seconds))
    return rows


# --- Output --------------------------------------------------------------------

_CSV_HEADER = ["config", "recall", "mean_latency_ms", "repeats", "n_probes"]


def format_table(rows: Sequence[SweepRow]) -> str:
    """Render rows as an aligned plain-text table (recall as a percentage)."""
    data = [
        [r.label, f"{r.recall:.0%}", f"{r.mean_latency_ms:.1f}", str(r.repeats), str(r.n_probes)]
        for r in rows
    ]
    widths = [len(h) for h in _CSV_HEADER]
    for row in data:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))

    def fmt(cells: Sequence[str]) -> str:
        return "  ".join(cell.ljust(widths[i]) for i, cell in enumerate(cells))

    lines = [fmt(_CSV_HEADER), fmt(["-" * w for w in widths])]
    lines.extend(fmt(row) for row in data)
    return "\n".join(lines)


def write_csv(rows: Sequence[SweepRow], path: Any) -> None:
    """Write rows to ``path`` as CSV (the ``results/`` artifact format)."""
    import csv

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(_CSV_HEADER)
        for r in rows:
            writer.writerow([r.label, f"{r.recall:.4f}", f"{r.mean_latency_ms:.2f}", r.repeats, r.n_probes])
