"""Agent configuration, loaded from environment variables.

Nothing about the model is hardcoded — region and model id come from the
environment so the same code runs against any Bedrock model without edits
(see the "externalize config" convention and ADR-002 in AGENTS.md).

Memory-related config is intentionally absent in Iteration 1; it arrives in
Iteration 3 as a separate injected object so the harness can sweep it.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_REGION = "us-east-1"
# A sensible default; override with BEDROCK_MODEL_ID. Verify availability in your
# region/account before relying on it (Bedrock model access is opt-in per model).
# Newer Claude models invoke via a cross-region inference profile (the "us." prefix),
# not the bare foundation-model id. Verified ACTIVE and working in this account.
# Find yours with: aws bedrock list-inference-profiles
DEFAULT_MODEL_ID = "us.anthropic.claude-haiku-4-5-20251001-v1:0"


@dataclass(frozen=True)
class AgentConfig:
    """Everything the agent needs to talk to Bedrock. Immutable on purpose."""

    region: str
    model_id: str
    system_prompt: str = "You are a concise, helpful assistant."

    def __post_init__(self) -> None:
        if not self.region:
            raise ValueError("AgentConfig.region must be set (env AWS_REGION).")
        if not self.model_id:
            raise ValueError("AgentConfig.model_id must be set (env BEDROCK_MODEL_ID).")


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
    )
