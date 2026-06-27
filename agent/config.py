"""Agent configuration, loaded from environment variables.

Nothing about the model is hardcoded — region and model id come from the
environment so the same code runs against any Bedrock model without edits
(see the "externalize config" convention and ADR-002 in AGENTS.md).

Memory-related config is intentionally absent in Iteration 1; it arrives in
Iteration 3 as a separate injected object so the harness can sweep it.
"""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from typing import Optional

DEFAULT_REGION = "us-east-1"
# A sensible default; override with BEDROCK_MODEL_ID. Verify availability in your
# region/account before relying on it (Bedrock model access is opt-in per model).
# Newer Claude models invoke via a cross-region inference profile (the "us." prefix),
# not the bare foundation-model id. Verified ACTIVE and working in this account.
# Find yours with: aws bedrock list-inference-profiles
DEFAULT_MODEL_ID = "us.anthropic.claude-haiku-4-5-20251001-v1:0"
# Default to 0 for determinism: the sweep harness needs runs to be as reproducible
# as possible so a recall change is attributable to the memory parameter, not to
# sampling noise (ADR-008). Override with BEDROCK_TEMPERATURE.
DEFAULT_TEMPERATURE = 0.0


@dataclass(frozen=True)
class AgentConfig:
    """Everything the agent needs to talk to Bedrock. Immutable on purpose."""

    region: str
    model_id: str
    system_prompt: str = "You are a concise, helpful assistant."
    temperature: float = DEFAULT_TEMPERATURE

    def __post_init__(self) -> None:
        if not self.region:
            raise ValueError("AgentConfig.region must be set (env AWS_REGION).")
        if not self.model_id:
            raise ValueError("AgentConfig.model_id must be set (env BEDROCK_MODEL_ID).")
        if not (0.0 <= self.temperature <= 1.0):
            raise ValueError("AgentConfig.temperature must be in [0.0, 1.0].")


@dataclass(frozen=True)
class MemoryConfig:
    """The single injected object that controls the agent's memory behaviour.

    This is the **sweep seam** (ADR-002): the harness varies one field at a time and
    rebuilds the session manager — the agent code never changes per run. Field names
    deliberately mirror the AgentCore Memory SDK (`RetrievalConfig.top_k`,
    `.relevance_score`, `AgentCoreMemoryConfig.batch_size`) so the mapping in
    `memory/` is one-to-one; verified against bedrock-agentcore 1.15.

    `enabled=False` is the **no-memory baseline** control every sweep needs (ADR-007):
    the agent runs with memory attachment skipped entirely.
    """

    memory_id: str
    namespace: str
    actor_id: str
    session_id: str
    top_k: int = 10
    relevance_score: float = 0.2
    batch_size: int = 1
    enabled: bool = True

    def __post_init__(self) -> None:
        if self.enabled and not self.memory_id:
            raise ValueError("MemoryConfig.memory_id must be set when enabled (env MEMORY_ID).")
        if self.enabled and not self.namespace:
            raise ValueError("MemoryConfig.namespace must be set when enabled (env MEMORY_NAMESPACE).")
        if not (0 < self.top_k <= 1000):
            raise ValueError("MemoryConfig.top_k must be in (0, 1000].")
        if not (0.0 <= self.relevance_score <= 1.0):
            raise ValueError("MemoryConfig.relevance_score must be in [0.0, 1.0].")
        if not (1 <= self.batch_size <= 100):
            raise ValueError("MemoryConfig.batch_size must be in [1, 100].")


def _load_dotenv_if_present() -> None:
    """Best-effort load of a local .env so `python -m agent.serve` just works.

    Optional: if python-dotenv isn't installed, real environment variables still
    work — we just skip the convenience. Never overrides already-set env vars.
    """
    try:
        from dotenv import load_dotenv  # type: ignore[import-not-found]
    except ImportError:
        return
    load_dotenv(override=False)


def load_config() -> AgentConfig:
    """Build an AgentConfig from environment variables.

    Reads AWS_REGION and BEDROCK_MODEL_ID (loading a local .env first if present),
    falling back to documented defaults so a local smoke run works without a fully
    populated environment.
    """
    _load_dotenv_if_present()
    return AgentConfig(
        region=os.getenv("AWS_REGION", DEFAULT_REGION),
        model_id=os.getenv("BEDROCK_MODEL_ID", DEFAULT_MODEL_ID),
        temperature=float(os.getenv("BEDROCK_TEMPERATURE", str(DEFAULT_TEMPERATURE))),
    )


def load_memory_config(
    *,
    enabled: Optional[bool] = None,
    actor_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> MemoryConfig:
    """Build a MemoryConfig from environment + per-run identifiers.

    `MEMORY_ID` and `MEMORY_NAMESPACE` come from Terraform outputs (Iteration 2).
    `actor_id` / `session_id` are usually generated per run (timestamped/uuid) so each
    run is isolated; pass them explicitly to pin a conversation across turns. The
    harness overrides the sweepable fields directly on the dataclass — this loader is
    just the default starting point.
    """
    _load_dotenv_if_present()
    enabled = (os.getenv("MEMORY_ENABLED", "1") == "1") if enabled is None else enabled
    return MemoryConfig(
        memory_id=os.getenv("MEMORY_ID", ""),
        namespace=os.getenv("MEMORY_NAMESPACE", ""),
        actor_id=actor_id or os.getenv("ACTOR_ID") or f"actor-{uuid.uuid4().hex[:12]}",
        session_id=session_id or os.getenv("SESSION_ID") or f"session-{uuid.uuid4().hex[:12]}",
        enabled=enabled,
    )
