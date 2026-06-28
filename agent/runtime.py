"""AgentCore Runtime entry point — the agent served as an HTTP container (Iteration 6).

Same agent, served a second way. `serve.py` is the CLI (one prompt, exits);
this is the long-lived HTTP server AgentCore Runtime hosts in a container. The
SDK's `BedrockAgentCoreApp` ships the required `/ping` (health) + `/invocations`
(work) contract and binds port 8080, so this file is a thin transport over
`run_once` — the agent/config/memory layers are untouched (the "served two ways,
no code change" rule on the status board, ADR-002 in spirit).

The entrypoint receives the invocation payload (`{"prompt": "..."}`) and returns
the reply as JSON. A fresh agent is built per invocation, like the CLI — memory
persistence is the AgentCore Memory layer's job (via MEMORY_ID in the env), not
process lifetime.

Run locally:  python -m agent.runtime          # serves on http://localhost:8080
Container:    this module's __main__ is the image CMD (see Dockerfile).
"""

from __future__ import annotations

from bedrock_agentcore.runtime import BedrockAgentCoreApp  # type: ignore[import-not-found]

from .core import run_once

app = BedrockAgentCoreApp()


@app.entrypoint
def invoke(payload: dict) -> dict:
    """Handle one /invocations request: {"prompt": str} -> {"reply": str}.

    `payload` is the parsed JSON body AgentCore delivers. We accept `prompt`
    (the lab's convention) or `input` (a common alias); `run_once` validates it's
    non-empty and raises a clear error otherwise.
    """
    prompt = payload.get("prompt") or payload.get("input") or ""
    return {"reply": run_once(prompt)}


if __name__ == "__main__":
    app.run()
