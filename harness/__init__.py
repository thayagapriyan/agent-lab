"""Sweep harness for Agent Memory Lab (Iteration 5).

Drives the experiment: vary ONE memory parameter over a list of values, run the fixed
probe set per value plus a no-memory baseline, average over repeats, and emit a
recall/latency table or CSV. ``sweep.py`` is the injectable core (offline-testable);
``run.py`` is the live CLI. The agent is never edited per run — only the injected
``MemoryConfig`` changes (ADR-002, ADR-003).
"""

from .sweep import (
    SWEEPABLE,
    SweepRow,
    build_variant_config,
    format_table,
    run_config,
    run_sweep,
    write_csv,
)

__all__ = [
    "SWEEPABLE",
    "SweepRow",
    "build_variant_config",
    "run_config",
    "run_sweep",
    "format_table",
    "write_csv",
]
