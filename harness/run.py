"""CLI for the sweep harness (Iteration 5).

    python -m harness.run --sweep top_k --values 1,3,5,10 [--repeats 3] [--settle 5] [--out results/top_k.csv]

Builds the base agent + memory config from the environment, sweeps ONE memory parameter
(always including the no-memory baseline), prints a recall/latency table, and optionally
writes CSV. Memory behaviour is injected per config — the agent code is never edited
(ADR-002). This is live: it calls Bedrock + AgentCore Memory, so it needs creds +
MEMORY_ID and costs money. Keep value lists and repeats small.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from agent.config import load_config, load_memory_config
from agent.core import build_agent
from harness.sweep import SWEEPABLE, format_table, run_sweep, write_csv


def _parse_values(raw: str) -> list[str]:
    values = [v.strip() for v in raw.split(",") if v.strip()]
    if not values:
        raise argparse.ArgumentTypeError("at least one value required (comma-separated)")
    return values


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="harness.run",
        description="Sweep one memory parameter against the fixed probe set and score recall.",
    )
    parser.add_argument("--sweep", required=True, choices=sorted(SWEEPABLE), help="memory parameter to vary")
    parser.add_argument("--values", required=True, type=_parse_values, help="comma-separated values, e.g. 1,3,5,10")
    parser.add_argument("--repeats", type=int, default=1, help="runs per config, averaged (ADR-008); default 1")
    parser.add_argument(
        "--settle", type=float, default=5.0,
        help="seconds to wait for async fact extraction between seed and ask; default 5",
    )
    parser.add_argument("--out", type=Path, default=None, help="optional CSV output path (e.g. results/top_k.csv)")
    args = parser.parse_args(argv)

    agent_cfg = load_config()
    base_mem_cfg = load_memory_config()  # MEMORY_ID/NAMESPACE from env; fresh actor/session

    def build(mem_cfg):
        return build_agent(config=agent_cfg, memory_config=mem_cfg)

    try:
        rows = run_sweep(
            args.sweep, args.values, base_mem_cfg, build,
            repeats=args.repeats, settle_seconds=args.settle,
        )
    except Exception as exc:  # surface creds/MEMORY_ID/validation problems clearly
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(format_table(rows))
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        write_csv(rows, args.out)
        print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
