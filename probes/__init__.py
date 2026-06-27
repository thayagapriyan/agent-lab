"""Probe set + scoring for Agent Memory Lab (Iteration 4).

The lab's measuring instrument: a fixed set of ``(seed, question, expected)``
triples (``probes.py``), a deterministic keyword scorer (``scoring.py``), and a
runner that plants a fact, probes recall, and times the answer (``runner.py``).
The Iteration 5 harness loops the runner over the probe set per memory config and
aggregates recall + latency. Pure stdlib — no AWS — so it stays offline-testable.
"""

from .probes import PROBES, Probe, load_probes
from .runner import run_probe
from .scoring import ProbeResult, score

__all__ = ["Probe", "PROBES", "load_probes", "score", "ProbeResult", "run_probe"]
