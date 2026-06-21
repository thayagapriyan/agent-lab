"""Iteration 1 smoke test: prompt -> response round trip.

Two modes (see TESTING.md):

* Default (mock): builds the agent with a fake model factory, so there are NO AWS
  calls and NO cost. Runs offline / in CI. Proves the agent wiring, the config
  seam, and run_once() work end to end.
* Live (RUN_LIVE=1): builds the real agent and calls Bedrock. Proves the actual
  Bedrock wiring. Needs AWS credentials + model access and costs a little.

Config (`AgentConfig`) is always tested directly since it has no external deps.
"""

from __future__ import annotations

import os

import pytest

from agent.config import AgentConfig, load_config
from agent.core import run_once


def test_config_loads_from_env(monkeypatch):
    monkeypatch.setenv("AWS_REGION", "eu-west-1")
    monkeypatch.setenv("BEDROCK_MODEL_ID", "some.model-id")
    cfg = load_config()
    assert cfg.region == "eu-west-1"
    assert cfg.model_id == "some.model-id"


def test_config_rejects_empty_region():
    with pytest.raises(ValueError):
        AgentConfig(region="", model_id="x")


class _FakeAgent:
    """Stand-in for a Strands Agent: echoes a canned reply, no network."""

    def __init__(self, reply: str) -> None:
        self._reply = reply
        self.last_prompt: str | None = None

    def __call__(self, prompt: str) -> str:
        self.last_prompt = prompt
        return self._reply


def test_round_trip_mocked():
    """Default path: a prompt goes in, a reply comes back — no AWS involved."""
    fake = _FakeAgent("pong")
    reply = run_once("ping", agent=fake)
    assert reply == "pong"
    assert fake.last_prompt == "ping"


def test_run_once_rejects_empty_prompt():
    with pytest.raises(ValueError):
        run_once("   ", agent=_FakeAgent("x"))


@pytest.mark.skipif(
    os.getenv("RUN_LIVE") != "1",
    reason="live Bedrock test; set RUN_LIVE=1 (needs AWS creds + model access, costs a little)",
)
def test_round_trip_live():
    """Opt-in: actually call Bedrock through the real agent."""
    reply = run_once("Reply with the single word: pong")
    assert isinstance(reply, str) and reply.strip()
