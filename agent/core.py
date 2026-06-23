"""Build and run the Strands agent.

The model is constructed behind a small factory (`build_model`) so the same agent
code can run against a real Bedrock model or a mock. This is the seam the smoke
test uses to stay free/offline by default, and the same "inject, don't hardcode"
spirit the memory config will follow in Iteration 3.

NOTE: the Strands SDK API evolves — `build_model` and `build_agent` deliberately
isolate the SDK-specific calls in one place. Verify class/argument names against
the current `strands-agents` docs before relying on them.
"""

from __future__ import annotations

from typing import Any, Callable, Optional

from .config import AgentConfig, MemoryConfig, load_config

# A model factory takes an AgentConfig and returns "something the agent can use as
# a model". Tests inject a fake; production uses the real Bedrock factory below.
ModelFactory = Callable[[AgentConfig], Any]

# A memory factory takes a MemoryConfig + region and returns a Strands session manager
# (or None to run without memory — the baseline). Tests inject a fake to stay offline.
MemoryFactory = Callable[[MemoryConfig, str], Any]


def build_model(config: AgentConfig) -> Any:
    """Construct a real Bedrock model for Strands from config.

    Imported lazily so the package (and the mocked smoke test) works even when
    `strands-agents` / AWS deps aren't installed yet.
    """
    from strands.models import BedrockModel  # type: ignore[import-not-found]

    return BedrockModel(model_id=config.model_id, region_name=config.region)


def _default_memory_factory(memory_config: MemoryConfig, region: str) -> Any:
    """Real session-manager factory (lazy import so offline paths skip the SDK)."""
    from memory import build_session_manager

    return build_session_manager(memory_config, region=region)


def build_agent(
    config: Optional[AgentConfig] = None,
    model_factory: ModelFactory = build_model,
    memory_config: Optional[MemoryConfig] = None,
    memory_factory: MemoryFactory = _default_memory_factory,
) -> Any:
    """Create a Strands Agent from config, using the given model + memory factories.

    Pass a custom `model_factory` (e.g. one returning a mock) to avoid any AWS calls —
    that is how the offline smoke test runs. Pass a `memory_config` to attach AgentCore
    Memory: the `memory_factory` turns it into a session manager (or None for the
    no-memory baseline). When memory is attached, the caller owns the lifecycle — close
    the manager at session end (see `memory.factory.close_session_manager`) or buffered
    writes are lost. Strands keeps the manager privately, so for a stable handle we also
    expose it on the returned agent as `.memory_session_manager` (None when no memory).
    """
    config = config or load_config()
    from strands import Agent  # type: ignore[import-not-found]

    model = model_factory(config)

    session_manager = None
    if memory_config is not None:
        session_manager = memory_factory(memory_config, config.region)

    # callback_handler=None disables Strands' default streaming-to-stdout, so the
    # caller (serve.py / the harness) owns output and we don't print twice.
    agent = Agent(
        model=model,
        system_prompt=config.system_prompt,
        callback_handler=None,
        session_manager=session_manager,
    )
    # Our own stable handle for the lifecycle contract (Strands stores it privately).
    agent.memory_session_manager = session_manager
    return agent


def run_once(prompt: str, agent: Optional[Any] = None) -> str:
    """Send one prompt to the agent and return its reply as a string.

    The smallest possible "does a round trip work?" surface. `agent` can be
    injected by tests; otherwise a default agent is built from env config.
    """
    if not prompt or not prompt.strip():
        raise ValueError("prompt must be a non-empty string")
    agent = agent or build_agent()
    result = agent(prompt)
    return str(result)
