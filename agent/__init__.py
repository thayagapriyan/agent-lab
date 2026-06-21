"""Agent Memory Lab — the Strands agent package.

Iteration 1: a minimal agent that answers a prompt locally, no memory yet.
See DESIGN.md (#1-agent-service) and DEVELOPMENT.md for context.
"""

from .config import AgentConfig, load_config
from .core import build_agent, run_once

__all__ = ["AgentConfig", "load_config", "build_agent", "run_once"]
