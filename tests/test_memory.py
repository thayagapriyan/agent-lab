"""Iteration 3 tests: attach memory to the agent via an injected config.

Mirrors the smoke test's philosophy (see AGENTS.md — How we test):

* Default: no AWS. Tests the config seam, validation, and that `build_agent` attaches
  whatever the memory factory returns — using a fake factory, so no SDK/AWS calls.
* `RUN_LIVE=1`: a real store-then-recall against the live AgentCore Memory resource.
  Needs MEMORY_ID + creds and costs a little.
"""

from __future__ import annotations

import os

import pytest

from agent.config import MemoryConfig, load_memory_config
from agent.core import build_agent
from memory.factory import build_session_manager, close_session_manager


# --- MemoryConfig: validation + the sweepable shape (no deps) -----------------

def test_memory_config_defaults_match_sdk():
    cfg = MemoryConfig(memory_id="m-1", namespace="semantic/{actorId}", actor_id="a", session_id="s")
    assert cfg.top_k == 10 and cfg.relevance_score == 0.2 and cfg.batch_size == 1
    assert cfg.enabled is True


@pytest.mark.parametrize(
    "kwargs",
    [
        {"top_k": 0},               # must be > 0
        {"relevance_score": 1.5},   # must be in [0, 1]
        {"batch_size": 0},          # must be >= 1
    ],
)
def test_memory_config_rejects_out_of_range(kwargs):
    base = dict(memory_id="m-1", namespace="ns", actor_id="a", session_id="s")
    with pytest.raises(ValueError):
        MemoryConfig(**{**base, **kwargs})


def test_memory_config_requires_id_when_enabled():
    with pytest.raises(ValueError):
        MemoryConfig(memory_id="", namespace="ns", actor_id="a", session_id="s", enabled=True)


def test_disabled_config_skips_requirements():
    # The no-memory baseline (ADR-007): no memory_id needed, nothing attaches.
    cfg = MemoryConfig(memory_id="", namespace="", actor_id="a", session_id="s", enabled=False)
    assert cfg.enabled is False


def test_load_memory_config_generates_ids(monkeypatch):
    monkeypatch.delenv("ACTOR_ID", raising=False)
    monkeypatch.delenv("SESSION_ID", raising=False)
    monkeypatch.setenv("MEMORY_ID", "m-123")
    monkeypatch.setenv("MEMORY_NAMESPACE", "semantic/{actorId}")
    cfg = load_memory_config()
    assert cfg.memory_id == "m-123"
    assert cfg.actor_id.startswith("actor-") and cfg.session_id.startswith("session-")


# --- The factory: disabled returns None without touching the SDK --------------

def test_build_session_manager_disabled_returns_none():
    cfg = MemoryConfig(memory_id="", namespace="", actor_id="a", session_id="s", enabled=False)
    # No bedrock-agentcore import happens on this path — safe offline.
    assert build_session_manager(cfg, region="us-east-1") is None


def test_close_session_manager_tolerates_none():
    close_session_manager(None)  # must not raise


# --- The attach seam: build_agent wires whatever the factory returns ----------

class _FakeModel:
    # Strands' Agent reads model.stateful during construction; provide it so we can
    # build a real Agent offline without a real model.
    stateful = False

    def __call__(self, *a, **k):  # pragma: no cover - never invoked here
        return "ok"


class _FakeSessionManager:
    """Stands in for a session manager; identity-checked after attach.

    Strands registers the session manager as a hook provider during Agent init, so it
    must implement register_hooks (a no-op here is enough for the offline attach test).
    """

    def register_hooks(self, registry, **kwargs):
        pass


def test_build_agent_attaches_session_manager_via_factory():
    sentinel = _FakeSessionManager()
    captured = {}

    def fake_memory_factory(mem_cfg, region):
        captured["region"] = region
        captured["memory_id"] = mem_cfg.memory_id
        return sentinel

    mem_cfg = MemoryConfig(memory_id="m-1", namespace="ns", actor_id="a", session_id="s")
    agent = build_agent(
        model_factory=lambda c: _FakeModel(),
        memory_config=mem_cfg,
        memory_factory=fake_memory_factory,
    )
    # The agent attached exactly what the factory produced — the injection seam works.
    assert agent.memory_session_manager is sentinel
    assert captured["memory_id"] == "m-1" and captured["region"]


def test_build_agent_without_memory_config_attaches_nothing():
    agent = build_agent(model_factory=lambda c: _FakeModel())
    assert agent.memory_session_manager is None


# --- Live: real store-then-recall against AgentCore Memory ---------------------

@pytest.mark.skipif(
    os.getenv("RUN_LIVE") != "1",
    reason="live memory test; set RUN_LIVE=1 (needs MEMORY_ID + AWS creds, costs a little)",
)
def test_store_then_recall_live():
    """Plant a fact in one turn, recall it in a later turn through memory.

    Uses a fresh actor/session so the run is isolated. batch_size=1 means writes are
    immediate; we still close the manager to flush per the lifecycle contract.
    """
    from agent.config import load_config

    mem_cfg = load_memory_config()  # MEMORY_ID/NAMESPACE from env; fresh actor/session
    assert mem_cfg.memory_id, "set MEMORY_ID in the environment for the live test"

    agent = build_agent(config=load_config(), memory_config=mem_cfg)
    try:
        agent("My favorite fruit is mango. Remember that.")
        reply = str(agent("What is my favorite fruit?"))
    finally:
        close_session_manager(agent.memory_session_manager)

    assert "mango" in reply.lower(), f"expected recall of 'mango', got: {reply!r}"
