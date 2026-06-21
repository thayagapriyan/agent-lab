# DEVELOPMENT.md

How to build and run **Agent Memory Lab** locally — tech stack, setup, project
layout, commands, conventions, and the gotchas that bite. If you write code in
this repo, read this first (after [ITERATION.md](ITERATION.md) for status and
[AGENTS.md](AGENTS.md) for the working loop).

> ◀ Pipeline: [IDEA.md](IDEA.md) → [DESIGN.md](DESIGN.md) → **DEVELOPMENT.md** →
> [TESTING.md](TESTING.md) → [DEPLOYMENT.md](DEPLOYMENT.md) ▶. The build plan /
> status is in [ITERATION.md](ITERATION.md); AWS account, IAM and cost are in
> [DEPLOYMENT.md](DEPLOYMENT.md). Full map:
> [documentation map](ITERATION.md#documentation-map).

## Tech stack

- **Language:** Python (3.10+). Python is required — the full AgentCore Memory
  system lives in the Python SDK; the TypeScript Memory module is not ready
  (ADR-001 in [DECISIONS.md](DECISIONS.md)).
- **Agent SDK:** Strands (`strands-agents`).
- **Memory:** AgentCore Memory via `bedrock-agentcore[strands-agents]`.
- **Runtime:** Amazon Bedrock AgentCore Runtime.
- **Model:** a Bedrock-hosted model (model ID via env var).

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install strands-agents 'bedrock-agentcore[strands-agents]'
# plus whatever the harness needs (e.g. a CSV/table lib)
```

You also need AWS credentials and a created memory resource before anything that
touches Bedrock or memory will run — see
[DEPLOYMENT.md → Infrastructure](DEPLOYMENT.md#part-1--infrastructure-aws-prerequisites).

Required environment variables (externalize everything; hardcode nothing):

- `AWS_REGION`
- `BEDROCK_MODEL_ID`
- `MEMORY_ID` — from the created AgentCore Memory resource
- `ACTOR_ID`, `SESSION_ID` — usually generated per run (timestamped)

## Project layout (target)

```
agent/        # Strands agent definition + tools + /ping, /invocations
memory/       # memory config builders, session-manager wiring
harness/      # sweep runner, scoring, table/CSV output
probes/       # fixed probe set (seed, question, expected)
scripts/      # one-time setup: create memory resource, IAM role
```

## Common commands

```bash
# Run the agent locally
python -m agent.serve

# Run the parameter sweep
python -m harness.run --sweep top_k --values 1,3,5,10

# Deploy to AgentCore Runtime  (see DEPLOYMENT.md)
agentcore deploy

# Tail runtime logs
aws logs tail /aws/bedrock-agentcore/runtimes/<name> --region $AWS_REGION --since 1h
```

> The `agentcore` CLI works the same for Python and TypeScript agents; the
> deployment flow is identical across both.

## Conventions

- **Inject memory config; never hardcode it.** All tunable memory settings flow
  through a single config object the harness can vary. If you find yourself editing
  agent logic to change a memory setting, stop — lift it into the config. (This is
  the [config seam](DESIGN.md#the-configuration-seam); ADR-002.)
- **One parameter per sweep.** A run changes exactly one memory parameter and holds
  the rest constant. Multi-parameter changes make results uninterpretable (ADR-003).
- **Keep the probe set fixed.** Don't edit `probes/` to make a run look better. If
  the probe set changes, prior results are no longer comparable; note it loudly
  (ADR-004).
- **Externalize config to env vars.** No hardcoded region, model ID, or memory ID.
- **One agent per session.** The AgentCore memory session manager currently
  supports a single agent per session. Don't attach multiple.

## Critical gotchas (read before touching memory code)

1. **Flush buffered memory.** When `batch_size > 1`, messages are buffered and only
   written when the buffer fills. Always use a context manager or call `close()` in
   a `finally` block when the session ends, or buffered memories are lost — and the
   harness will report falsely low recall.
2. **Namespace consistency.** The namespace set at strategy-creation time must match
   the one referenced at retrieval. A mismatch returns nothing, silently.
3. **Warm up before timing.** The first invocation after deploy is a cold start;
   discard it before recording latency, or your numbers are skewed.
4. **Verify SDK field names against current docs.** The AgentCore Memory SDK
   evolves. Don't trust parameter names from memory or from older examples — confirm
   against the current AWS docs before relying on them.

## When extending

- Adding a new sweepable parameter? Wire it through the config object and the
  harness's sweep selector; don't special-case it in agent logic.
- Adding probes? Add them as `(seed, question, expected)` triples and treat the
  expanded set as a new baseline — re-run prior configs if you need comparison.
- Considering a TypeScript port? Possible for the agent + Runtime deployment, but
  you'd hand-build the memory layer today since the managed Memory module isn't in
  the TS SDK yet. Confirm the SDK's current state before committing to it.

## Scope guardrails

This is a **learning lab, not production**. Don't add auth hardening, multi-tenancy,
SLAs, or large benchmark suites unless explicitly asked — they work against the
project's purpose, which is a small, fast, repeatable memory experiment.
