"""Memory layer for Agent Memory Lab.

Iteration 3: turn an injected `MemoryConfig` into an AgentCore Memory session manager
the Strands agent can attach. All SDK-specific calls live here (mirroring the
`build_model` factory in `agent/core.py`) so the agent stays unaware of memory wiring
and the harness can sweep memory parameters by varying only the config object.
"""

from .factory import build_session_manager

__all__ = ["build_session_manager"]
