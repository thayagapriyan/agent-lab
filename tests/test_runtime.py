"""Iteration 6: the AgentCore Runtime entrypoint maps a payload to a reply.

Offline — the entrypoint is a thin transport over `run_once`, so we stub that out
and assert the payload→reply mapping (no AWS, no Bedrock). The /ping + /invocations
HTTP wiring itself is the SDK's `BedrockAgentCoreApp`, tested by AWS, not us; what's
ours to verify is the one function we wrote.
"""

from __future__ import annotations

import pytest

from agent import runtime


def test_entrypoint_maps_prompt_to_reply(monkeypatch):
    monkeypatch.setattr(runtime, "run_once", lambda p: f"reply to {p}")
    assert runtime.invoke({"prompt": "hello"}) == {"reply": "reply to hello"}


def test_entrypoint_accepts_input_alias(monkeypatch):
    monkeypatch.setattr(runtime, "run_once", lambda p: p.upper())
    assert runtime.invoke({"input": "hi"}) == {"reply": "HI"}


def test_entrypoint_rejects_empty_payload():
    # No prompt/input -> run_once gets "" -> its own non-empty guard fires.
    with pytest.raises(ValueError):
        runtime.invoke({})
