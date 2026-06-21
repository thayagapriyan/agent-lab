# DEVELOPMENT.md

How to build and run **Agent Memory Lab** — and **where the project stands**. This
is the **read-first doc**: tech stack, setup, commands, conventions, gotchas, *and*
the status board + iteration plan. If you're picking up this project (AI or human),
start here, then read [AGENTS.md](AGENTS.md) for the working loop.

> ◀ Pipeline: [IDEA.md](IDEA.md) → [DESIGN.md](DESIGN.md) → **DEVELOPMENT.md** →
> [TESTING.md](TESTING.md) → [DEPLOYMENT.md](DEPLOYMENT.md) ▶. AWS account, IAM and
> cost are in [DEPLOYMENT.md](DEPLOYMENT.md). Full map:
> [documentation map](AGENTS.md#documentation-map).
>
> **Jump to:** [Status board](#status-board) · [Iteration plan](#iteration-plan) ·
> [Setup](#setup) · [Common commands](#common-commands).

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
python -m venv .venv
# Windows (PowerShell): .venv\Scripts\Activate.ps1   |   Git Bash: source .venv/Scripts/activate
# macOS/Linux:          source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then fill in AWS_REGION / BEDROCK_MODEL_ID
```

The **mocked smoke test runs with no AWS at all**. For anything that hits Bedrock
(the live test, `agent.serve`) you need AWS credentials and Bedrock model access —
see [DEPLOYMENT.md → Infrastructure](DEPLOYMENT.md#part-1--infrastructure-aws-prerequisites)
and provision with Terraform (`infra/`).

Environment variables (externalize everything; hardcode nothing). See
[.env.example](.env.example):

- `AWS_REGION`, `BEDROCK_MODEL_ID` — used now (Iteration 1).
- `MEMORY_ID` — Iteration 2, from the created AgentCore Memory resource.
- `ACTOR_ID`, `SESSION_ID` — Iteration 3, usually generated per run (timestamped).
- `RUN_LIVE=1` — opt the smoke test into a real Bedrock call (costs a little).

## Project layout

Exists now (Iteration 1):

```
agent/        # Strands agent: config (env), core (build/run), serve (CLI)
infra/        # Terraform: IAM role/policy for Bedrock invoke (Bedrock access only)
scripts/      # verify_bedrock.sh — AWS CLI check of model access
tests/        # smoke test (mock by default, RUN_LIVE=1 for real Bedrock)
```

Planned (later iterations):

```
memory/       # Iteration 3: memory config builders, session-manager wiring
probes/       # Iteration 4: fixed probe set (seed, question, expected)
harness/      # Iteration 5: sweep runner, scoring, table/CSV output
```

## Common commands

```bash
# Run the mocked smoke test (free, offline)
python -m pytest -q

# Run the live smoke test against real Bedrock (needs creds + access; costs a little)
RUN_LIVE=1 python -m pytest -q tests/test_smoke.py::test_round_trip_live

# Run the agent locally (one prompt)
python -m agent.serve "hello, who are you?"

# Verify Bedrock access independently, via the AWS CLI (no model invocation)
bash scripts/verify_bedrock.sh

# Provision Bedrock-access infra (from infra/)
cd infra && terraform init && terraform plan && terraform apply

# --- later iterations ---
# python -m harness.run --sweep top_k --values 1,3,5,10   # Iteration 5
# agentcore deploy                                          # Iteration 6 (see DEPLOYMENT.md)
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

---

# Iterations — status & plan

**The single source of truth for project status.** This section tracks where the
project is and what to do next. The work is split into small, shippable iterations,
each with a goal, a definition of done, and a checklist. Tick boxes and update the
status board as you go (per the [agent working loop](AGENTS.md#agent-working-loop));
record *how* in [CHANGELOG.md](CHANGELOG.md).

## Status board

Update this table whenever an iteration changes state.

| Iteration | Goal | Status | Notes |
|-----------|------|--------|-------|
| 0 | Project scaffold & docs wiring | ✅ Done | Doc system created. |
| 1 | Minimal local Strands agent | ✅ Done | + Terraform (Bedrock access), AWS CLI verify. |
| 2 | Create AgentCore Memory resource | ⬜ Not started | Setup + IDs in env. |
| 3 | Attach memory to the agent | ⬜ Not started | Inject config, one strategy. |
| 4 | Probe set + scoring | ⬜ Not started | Fixed (seed, question, expected). |
| 5 | Sweep harness | ⬜ Not started | Sweep one param, emit table/CSV. |
| 6 | Deploy to AgentCore Runtime | ⬜ Not started | `/ping` + `/invocations`, no code change. |
| 7 | First full sweep + writeup | ⬜ Not started | Run, read the table, explain it. |

**Status legend:** ⬜ Not started · 🔵 In progress · ✅ Done · ⚠️ Blocked

**Currently in progress:** _none_
**Next up:** Iteration 2 — Create AgentCore Memory resource.

## Iteration plan

Each iteration is a small, shippable slice with a **goal**, a **definition of done**
(so any agent knows when to stop), and a **task checklist**. Keep iterations small
enough to finish and document in one sitting.

> The plan below is the roadmap. Refine it as you learn — but if you change an
> iteration's goal or scope, say so in [CHANGELOG.md](CHANGELOG.md) so the history
> stays honest.

### Iteration 0 — Project scaffold & docs wiring ✅

**Goal:** Establish the documentation system so future agents can self-orient.

**Done when:**
- [x] A read-first status doc exists with a status board and iteration plan (this
      section of DEVELOPMENT.md).
- [x] `CHANGELOG.md` exists and is ready for append-only entries.
- [x] Every `.md` file links to the others (documentation map).
- [x] `AGENTS.md` describes the mandatory agent working loop.

### Iteration 1 — Minimal local Strands agent ✅

**Goal:** A Strands agent that answers a prompt locally, no memory yet.

**Done when:**
- [x] `agent/` package with a Strands `Agent` and a Bedrock model.
- [x] Runs locally (`python -m agent.serve` or direct call) and returns a reply.
- [x] Model ID and region read from env vars (no hardcoding).
- [x] A smoke test confirms a prompt → response round trip (mock by default,
      `RUN_LIVE=1` for real Bedrock).

**Also delivered (per user request this iteration):**
- [x] **Terraform** (`infra/`) provisioning Bedrock access (IAM role + scoped
      `bedrock:InvokeModel` policy). Scope: Bedrock only; memory/Runtime later.
- [x] **AWS CLI** verification script (`scripts/verify_bedrock.sh`).
- [x] `.gitignore`, `requirements.txt`, `.env.example`.

**Notes / pointers:** see [DESIGN.md](DESIGN.md#1-agent-service) and the env vars in
[Setup](#setup). API names (`strands.Agent`, `strands.models.BedrockModel`) verified
against the installed SDK.

### Iteration 2 — Create AgentCore Memory resource ⬜

**Goal:** A managed memory resource exists and its ID is available to the agent.

**Done when:**
- [ ] One-time setup creates the memory resource (extend `infra/` and/or `scripts/`).
- [ ] At least one strategy configured (start with *semantic*).
- [ ] `MEMORY_ID` documented and consumed from env.
- [ ] Namespace scheme written down (it must match at retrieval time).

### Iteration 3 — Attach memory to the agent ⬜

**Goal:** The agent reads/writes memory via an **injected** config object.

**Done when:**
- [ ] `memory/` builds an `AgentCoreMemorySessionManager` from a config object.
- [ ] Agent stores a fact in one turn and recalls it in a later turn.
- [ ] Config is injected, not hardcoded (this is the sweep seam).
- [ ] Session is always flushed/closed (no lost buffered writes).

### Iteration 4 — Probe set + scoring ⬜

**Goal:** A fixed probe set and a way to score recall/relevance.

**Done when:**
- [ ] `probes/` holds `(seed, question, expected)` triples, kept fixed.
- [ ] A scorer judges recall and relevance for one answer (start simple:
      keyword/substring match — see ADR-006 in [DECISIONS.md](DECISIONS.md)).
- [ ] Latency captured per turn.
- [ ] Scoring is identical across runs (so a sweep stays comparable).

### Iteration 5 — Sweep harness ⬜

**Goal:** Sweep one memory parameter across values and emit a comparison table.

**Done when:**
- [ ] `harness/` runs the full probe set per config.
- [ ] `--sweep <param> --values <list>` works for at least `top_k`.
- [ ] A **no-memory baseline** run is included as the control (ADR-007).
- [ ] Nondeterminism handled: temperature 0 and/or N repeats averaged (ADR-008).
- [ ] Output is a side-by-side table / CSV (recall, relevance, latency), written to
      [RESULTS.md](RESULTS.md).
- [ ] Exactly one parameter varies per run (others held constant).

### Iteration 6 — Deploy to AgentCore Runtime ⬜

**Goal:** Same agent code runs on AgentCore Runtime with no changes.

**Done when:**
- [ ] `/ping` and `/invocations` contract satisfied.
- [ ] `agentcore deploy` produces a working runtime.
- [ ] Runtime points at the same memory resource by ID.
- [ ] Logs visible (CloudWatch).

### Iteration 7 — First full sweep + writeup ⬜

**Goal:** Run a real sweep, read the table, explain the result.

**Done when:**
- [ ] One parameter swept end to end against the probe set.
- [ ] A short writeup explains *why* recall/relevance/latency moved.
- [ ] Findings appended to [RESULTS.md](RESULTS.md) and [CHANGELOG.md](CHANGELOG.md).

## Parking lot

Ideas and follow-ups that are **not** in the current plan. Pull them into a real
iteration when ready; don't act on them silently. (See stretch ideas in
[IDEA.md](IDEA.md#stretch-ideas-later-not-now).)

- Swap embedding models and re-run the sweep.
- Add recency/decay weighting; measure effect on old vs. new facts.
- TypeScript port once the managed Memory module ships.
