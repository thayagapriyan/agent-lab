"""Build an AgentCore Memory session manager from an injected MemoryConfig.

This is the memory equivalent of `agent.core.build_model`: a single factory that maps
our framework-neutral `MemoryConfig` onto the AgentCore Memory SDK objects. Keeping the
SDK calls in one place means:

* the agent code never imports the memory SDK directly (clean attachment seam), and
* the harness sweeps a parameter by changing one `MemoryConfig` field and rebuilding —
  no agent change per run (ADR-002, ADR-003).

Field mapping (verified against bedrock-agentcore 1.15):
    MemoryConfig.top_k          -> RetrievalConfig.top_k
    MemoryConfig.relevance_score-> RetrievalConfig.relevance_score
    MemoryConfig.namespace      -> the KEY in AgentCoreMemoryConfig.retrieval_config map
    MemoryConfig.batch_size     -> AgentCoreMemoryConfig.batch_size
    MemoryConfig.enabled=False  -> no session manager at all (no-memory baseline, ADR-007)

The SDK imports are lazy so the package (and the offline smoke test) works without the
memory deps installed.
"""

from __future__ import annotations

from typing import Any, Optional

from agent.config import MemoryConfig


def build_session_manager(config: MemoryConfig, *, region: str) -> Optional[Any]:
    """Return an AgentCoreMemorySessionManager for this config, or None.

    Returns ``None`` when ``config.enabled`` is False — the agent then runs with no
    memory attached, which is the control baseline every sweep is measured against.
    The returned manager buffers writes when ``batch_size > 1``; the caller MUST close
    it at session end or buffered memories are lost (see `close_session_manager`).
    """
    if not config.enabled:
        return None

    from bedrock_agentcore.memory.integrations.strands.config import (
        AgentCoreMemoryConfig,
        RetrievalConfig,
    )
    from bedrock_agentcore.memory.integrations.strands.session_manager import (
        AgentCoreMemorySessionManager,
    )

    # retrieval_config is a map of namespace -> RetrievalConfig. The namespace must
    # match the strategy's namespace, or retrieval silently returns nothing.
    retrieval = {
        config.namespace: RetrievalConfig(
            top_k=config.top_k,
            relevance_score=config.relevance_score,
        )
    }

    agentcore_config = AgentCoreMemoryConfig(
        memory_id=config.memory_id,
        actor_id=config.actor_id,
        session_id=config.session_id,
        retrieval_config=retrieval,
        batch_size=config.batch_size,
    )

    return AgentCoreMemorySessionManager(agentcore_config, region_name=region)


def close_session_manager(session_manager: Optional[Any]) -> None:
    """Flush and close a session manager so buffered writes aren't lost.

    Safe to call with ``None`` (the disabled/baseline case). When ``batch_size > 1``,
    messages are buffered and only written when the buffer fills — ``close()`` flushes
    the last partial batch, without which it is dropped and recall scores would be
    falsely low. ``close`` is the SDK's teardown method (verified against
    bedrock-agentcore 1.15); guarded with getattr to tolerate SDK drift.
    """
    if session_manager is None:
        return
    close = getattr(session_manager, "close", None)
    if callable(close):
        close()
