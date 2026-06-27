"""Run one probe against an agent (or a pair of agents) and score the result.

Seed the fact, ask the question, time the *question* turn, score the answer. The
agent is passed in — the runner never builds or configures it (ADR-002: memory
behaviour is chosen when the harness *builds* the agent, not here). This is the
single unit the Iteration 5 sweep harness loops over.

Short-term vs long-term — the distinction that makes the baseline meaningful:

* Pass ONE agent (``question_agent=None``) and both turns share a conversation, so
  **short-term** memory holds the seed — even a no-memory agent recalls it. Good
  for measuring short-term behaviour; useless as a long-term test.
* Pass a SEPARATE ``question_agent`` (new session, same actor) and the seed is gone
  from short-term, so only **long-term** memory can surface it. That is the real
  cross-session recall test the no-memory baseline (ADR-007) is compared against.

Lifecycle (flushing buffered writes before the question turn, and the async
extraction lag / repeats for the cross-session case) is the *caller's* job — the
harness handles it. The runner stays a single deterministic pass so scoring is
identical across runs.
"""

from __future__ import annotations

import time
from typing import Any, Optional

from .probes import Probe
from .scoring import ProbeResult, score


def run_probe(probe: Probe, seed_agent: Any, question_agent: Optional[Any] = None) -> ProbeResult:
    """Plant ``probe.seed`` on ``seed_agent``, ask ``probe.question``, time + score it.

    ``question_agent`` defaults to ``seed_agent`` (same-session). Only the question
    turn is timed; the seed turn is setup. Returns a :class:`ProbeResult`.
    """
    asker = question_agent if question_agent is not None else seed_agent

    seed_agent(probe.seed)  # plant the fact (not timed)

    start = time.perf_counter()
    answer = str(asker(probe.question))
    latency_ms = (time.perf_counter() - start) * 1000.0

    return ProbeResult(
        probe=probe,
        answer=answer,
        correct=score(answer, probe.expected),
        latency_ms=latency_ms,
    )
