"""Local entry point for the agent.

Iteration 1 keeps this deliberately minimal: a CLI that sends one prompt to the
agent and prints the reply. The AgentCore HTTP contract (/ping, /invocations)
arrives in Iteration 6 (see DEPLOYMENT.md) — the same agent code, served two ways.

Usage:
    python -m agent.serve "your prompt here"
    python -m agent.serve            # prompts interactively for one line
"""

from __future__ import annotations

import sys

from .core import run_once


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    prompt = " ".join(argv).strip() if argv else input("prompt> ").strip()
    if not prompt:
        print("No prompt given.", file=sys.stderr)
        return 2
    try:
        reply = run_once(prompt)
    except Exception as exc:  # surface real cause (e.g. missing AWS creds) clearly
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(reply)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
