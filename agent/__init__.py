"""Agent Memory Lab — the Strands agent package.

A minimal Strands agent that answers prompts locally and, as of Iteration 3, can
attach AgentCore Memory via an injected MemoryConfig (the sweep seam).
See AGENTS.md (Architecture / Tech stack) for context.
"""

from .config import AgentConfig, MemoryConfig, load_config, load_memory_config
from .core import build_agent, run_once

__all__ = [
    "AgentConfig",
    "MemoryConfig",
    "load_config",
    "load_memory_config",
    "build_agent",
    "run_once",
]
