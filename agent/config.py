"""Agent configuration, loaded from environment variables.

Nothing about the model is hardcoded — region and model id come from the
environment so the same code runs against any Bedrock model without edits
(see the "externalize config" convention in DEVELOPMENT.md and ADR-002).

Memory-related config is intentionally absent in Iteration 1; it arrives in
Iteration 3 as a separate injected object so the harness can sweep it.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_REGION = "us-east-1"
# A sensible default; override with BEDROCK_MODEL_ID. Verify availability in your
# region/account before relying on it (Bedrock model access is opt-in per model).
DEFAULT_MODEL_ID = "anthropic.claude-3-5-haiku-20241022-v1:0"


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


def load_config() -> AgentConfig:
    """Build an AgentConfig from environment variables.

    Reads AWS_REGION and BEDROCK_MODEL_ID, falling back to documented defaults so
    a local smoke run works without a fully populated environment.
    """
    return AgentConfig(
        region=os.getenv("AWS_REGION", DEFAULT_REGION),
        model_id=os.getenv("BEDROCK_MODEL_ID", DEFAULT_MODEL_ID),
    )
