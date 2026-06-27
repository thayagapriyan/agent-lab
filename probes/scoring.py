"""Score an answer against a probe's expected keywords (ADR-006).

Keyword/substring match, case-insensitive: the answer is correct if it contains
ANY expected keyword. Cheap, deterministic, transparent — and, crucially,
**identical across every run in a sweep**, or the comparison is meaningless. Move
to LLM-as-judge only if this proves too brittle (a deliberate, clearly labeled
change, since the judge adds its own error).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .probes import Probe


def score(answer: str, expected: Iterable[str]) -> bool:
    """True if ``answer`` contains any expected keyword (case-insensitive substring)."""
    haystack = answer.lower()
    return any(keyword.lower() in haystack for keyword in expected)


@dataclass(frozen=True)
class ProbeResult:
    """The outcome of running one probe: what was answered, was it recalled, how slow.

    ``latency_ms`` times only the *question* turn (the thing we measure), not the
    seed turn (setup). The harness (Iteration 5) aggregates these across the probe
    set into recall accuracy + latency for one config.
    """

    probe: Probe
    answer: str
    correct: bool
    latency_ms: float
