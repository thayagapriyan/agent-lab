# AGENTS.md

The **one guide for any agent (AI or human) working in this repo.** Read it before
making changes. It follows the `AGENTS.md` convention — the single place that tells a
coding agent what this project is, how it's built, the conventions that must not
break, where things stand, and how to ship. There are deliberately **no other `.md`
files**; everything an agent needs lives here or in the code.

---

## Working agreement (read before changing infra or CI/CD)

This project has a **sibling reference**, [agentcore-multiagent](../agentcore-multiagent),
and a shared **[aws-foundation](../aws-foundation)** repo for account-wide singletons.
Most of the churn in this repo's history came from ignoring that. The rules:

1. **The sibling/foundation are the source of truth — not whatever already exists here.**
   When asked to "copy" or "match" the sibling, FIRST read the sibling's actual files
   (`infra/*.tf`, `.github/workflows/*`), THEN reconcile this repo against them. Files
   already in this repo may be *drift*, not precedent — don't build on them blindly.
2. **Survey before you build.** Before adding infra/CI, list what exists in BOTH repos
   (`git ls-files`, the `infra/` tree, `.github/workflows/`, the `aws-foundation`
   layout). Present the gap and chosen approach in ONE message, then act — don't
   discover divergences one round at a time.
3. **Account-wide singletons are referenced, never created here.** The GitHub OIDC
   provider and the shared tfstate S3 bucket are one-per-account and shared across
   repos; they are owned by **[aws-foundation](../aws-foundation)**. This repo only
   *references* them (a `data` source / a `backend` pointing at the existing bucket). A
   `terraform destroy` here must never be able to delete something another repo needs.
4. **Per-repo, scoped resources stay here.** This repo owns its own deploy role (scoped
   to `agent-memory-lab-*`) and its own state *key* — in `infra/cicd.tf` /
   `infra/backend.tf`, mirroring the sibling.
5. **Name the trade-off out loud.** If an approach diverges from the sibling or the
   foundation model, say so and why in the same message — don't let divergence be silent.

---

## What this project is

**Agent Memory Lab** — a small Python [Strands](https://strandsagents.com) agent on
**Amazon Bedrock AgentCore Runtime**, plus a harness that **measures how the agent's
memory behaves as you change parameters**. It is a **learning lab, not production**.

**The core question:** *when I change a memory parameter, how does the agent's ability
to remember change?* Most tutorials show *how* to attach memory; this project measures
*how memory behaves* when you tune it. The point of the codebase is the experiment —
changes must preserve the ability to sweep **one memory parameter at a time** against a
**fixed probe set** and read a table of recall / relevance / latency.

### Memory vocabulary (what we sweep, what we don't)

"Memory" is several mechanisms stacked together. This lab fully sweeps the
**long-term / retrieval (RAG) layer** (the richest part), sweeps **short-term** with
one knob, and treats the rest as context it *uses or works around*:

| Term | Plain meaning | In this lab |
|------|---------------|-------------|
| **Long-term memory** | Facts/preferences remembered **across sessions** (AgentCore *strategies*: semantic / summarization / user-preference). | ✅ Swept (core) |
| **Retrieval / RAG** | Store info, fetch only the relevant bits at query time (top-k, relevance threshold, namespace). AgentCore Memory *is* a managed RAG system. | ✅ Swept (core) |
| **Short-term memory** | Recent turns kept verbatim in the context window (conversation window). | 🟡 Swept (one knob) |
| **Session memory** | Conversation persisted across restarts. On/off, not a dial. | 🔵 Used, not swept |
| **Context window** | The model's fixed input size. A constraint, not a variable. | ⚪ Fixed |
| **Embedding** | Text → vector so "similar meaning" = "close in space". | 🟣 Stretch only |

### Parameters under test

One varies per run, the rest held constant:

| Parameter | Layer | Controls | Why it matters |
|-----------|-------|----------|----------------|
| Memory strategy | Long-term | semantic / summarization / user-preference / combined | Biggest lever; changes what gets stored at all |
| Retrieval top-k | RAG | How many memories pulled per query | Too few misses facts; too many adds noise |
| Relevance threshold | RAG | Cutoff for "relevant enough" | Trades recall against precision |
| Namespace scope | RAG | strategy / actor / session granularity | Controls what the agent can even see |
| Batch size | Write path | Messages buffered before a write | Throughput vs. risk of losing buffered data |
| Conversation window | Short-term | Turns kept verbatim before summarizing | Short-term recall vs. context cost |

**Measured per config:** recall accuracy, relevance, latency. A **run** = (one config)
× (the fixed probe set).

### Non-goals

Not production. **Don't add** auth hardening, multi-tenancy, SLAs, large benchmark
suites, or multi-agent orchestration unless explicitly asked — they work against the
project's purpose (a small, fast, repeatable memory experiment). One agent, one memory
store, kept deliberately simple.

---

## Architecture

```
                       ┌──────────────────────────────┐
                       │       Experiment Harness       │
                       │   (sweep configs, score runs)  │
                       └───────────────┬────────────────┘
                                       │ invokes with a config
                                       ▼
   ┌─────────────┐    /invocations   ┌──────────────────┐
   │  Probe set  │ ────────────────▶ │   Agent Service   │
   │ (questions) │                   │  (Strands Agent)  │
   └─────────────┘ ◀──────────────── │   + tools         │
                       answers       └────────┬──────────┘
                                              │ session_manager
                                              ▼
                                   ┌──────────────────────┐
                                   │  AgentCore Memory      │
                                   │  strategies + retrieval│
                                   └──────────────────────┘
```

**Four parts:** a fixed **probe set**, **one agent** (Strands), a managed **AgentCore
Memory** layer, and an **experiment harness** that sweeps one parameter and scores the
result. The same agent code runs **locally** (HTTP server / direct calls) and **on
AgentCore Runtime** (containerized, behind `/ping` + `/invocations`) with no code
changes.

### The one rule that makes the lab work: inject config, never rebuild the agent

You build **one** agent app. To test a different memory configuration you **do not
touch the agent** — you pass it a different **config object**. If you ever find
yourself editing agent logic to change a memory setting, **stop** — lift it into the
config. That edit is the signal the design has been broken. The harness sweeps by
constructing variant configs; the agent reads its memory behavior entirely from that
one injected object (the "configuration seam").

```python
# illustrative shape — confirm exact fields against current SDK docs
config = AgentCoreMemoryConfig(
    memory_id=MEM_ID, actor_id=ACTOR_ID, session_id=SESSION_ID,
    retrieval_config={"top_k": 3, "relevance_threshold": 0.5},  # swept
)
```

**Build once, run many.** Building the harness (the iterations below) is different
from running sweeps. Once the machinery exists, sweeping `top_k`, then
`relevance_threshold`, then `strategy` is just *running the same harness with different
flags* — those are **runs, not new iterations**.

---

## Tech stack

- **Language:** Python (3.10+). Required — the full AgentCore Memory system lives in
  the Python SDK; the TypeScript Memory module is not ready (see ADR-001).
- **Agent SDK:** Strands (`strands-agents`).
- **Memory:** AgentCore Memory via `bedrock-agentcore[strands-agents]`.
- **Runtime:** Amazon Bedrock AgentCore Runtime.
- **Model:** a Bedrock-hosted model (id via env var; default
  `us.anthropic.claude-haiku-4-5-20251001-v1:0`).
- **Infra:** Terraform (AWS provider ≥ 5.0; 6.51 has the AgentCore Memory resources),
  S3 remote state with native locking.
- **CI/CD:** GitHub Actions + AWS OIDC (no stored keys).

---

## Setup & common commands

```bash
python -m venv .venv
# Windows (PowerShell): .venv\Scripts\Activate.ps1   |  Git Bash: source .venv/Scripts/activate
# macOS/Linux:          source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then fill in AWS_REGION / BEDROCK_MODEL_ID / MEMORY_ID
```

```bash
# Mocked smoke test (free, offline — what CI runs)
python -m pytest -q

# Live smoke test against real Bedrock (needs creds + model access; costs a little)
RUN_LIVE=1 python -m pytest -q tests/test_smoke.py::test_round_trip_live

# Run the agent locally (one prompt)
python -m agent.serve "hello, who are you?"

# Verify Bedrock access via AWS CLI (no model invocation)
bash scripts/verify_bedrock.sh

# Provision infra (see "Infrastructure & deploy" for fresh-clone bootstrap order)
cd infra && terraform init && terraform plan && terraform apply

# --- later iterations ---
# python -m harness.run --sweep top_k --values 1,3,5,10   # Iteration 5
# agentcore deploy                                          # Iteration 6
```

### Environment / config (externalize everything; hardcode nothing)

| Variable | Meaning | When |
|----------|---------|------|
| `AWS_REGION` | Region for Bedrock + AgentCore | now |
| `BEDROCK_MODEL_ID` | The model the agent invokes (must be enabled in your account) | now |
| `MEMORY_ID` | The created AgentCore Memory resource (`terraform output memory_id`) | Iter 2+ |
| `MEMORY_NAMESPACE` | Must match what the agent references at retrieval | Iter 2+ |
| `ACTOR_ID`, `SESSION_ID` | Who/which conversation memories belong to (generated per run) | Iter 3+ |
| `RUN_LIVE=1` | Opt the smoke test into a real Bedrock call | optional |

> Never commit credentials or a real `.env`. The mocked smoke test runs with **no AWS
> at all**; anything hitting Bedrock needs credentials + per-model access (opt-in).

### Project layout

```
agent/        # Strands agent: config.py (env), core.py (build/run + model factory), serve.py (CLI)
infra/        # Terraform: IAM (Bedrock invoke), memory.tf (AgentCore Memory), cicd.tf (OIDC deploy role), S3 backend
  bootstrap/      # one-time, LOCAL state: creates the S3 state bucket
scripts/      # verify_bedrock.sh — AWS CLI check of model access
tests/        # smoke test (mock by default, RUN_LIVE=1 for real Bedrock)
.github/workflows/  # bootstrap.yml (one-time OIDC) + deploy.yml (CI tests + TF apply)
# planned: memory/ (Iter 3), probes/ (Iter 4), harness/ (Iter 5)
```

---

## Conventions (don't break these)

- **Inject memory config; never hardcode it** (ADR-002). All tunable memory settings
  flow through one config object the harness varies — the design seam; protect it.
- **One parameter per sweep** (ADR-003). Multi-parameter changes make results
  uninterpretable.
- **Keep the probe set fixed** (ADR-004). Don't edit `probes/` to flatter a run; a
  changed probe set is a new baseline — say so loudly and re-run prior configs.
- **Externalize config to env vars.** No hardcoded region, model id, account id, or
  memory id.
- **One agent, one session per run.** The AgentCore session manager supports a single
  agent per session; don't attach multiple.
- **Ask before destructive/outward ops.** Don't run `terraform apply`/`destroy`,
  `git push`, or `git commit`, or delete cloud resources, without confirming.
- **Don't add comments** that just restate the code; comment only non-obvious *why*.

---

## Critical gotchas (read before touching these areas)

**Bedrock model ids (verified live, Iteration 1):**
- **Newer Claude models need an inference profile, not the bare id.** Invoking
  `anthropic.claude-haiku-4-5-...` directly fails; use the cross-region profile id
  `us.anthropic.claude-haiku-4-5-...`. List with `aws bedrock list-inference-profiles`.
- **"Legacy" models can be blocked.** `claude-3-haiku-20240307` returns *marked as
  Legacy and you have not been actively using the model* — pick an ACTIVE model.
- **IAM for inference profiles is broader.** The role must allow `InvokeModel` on
  *both* the `inference-profile/...` ARN and the underlying `foundation-model/...` ARNs
  (any region the profile spans). [`infra/iam.tf`](infra/iam.tf) handles this.

**Memory code (apply from Iteration 3 on):**
1. **Flush buffered memory.** With `batch_size > 1`, messages are buffered and written
   only when the buffer fills. Always close the session (context manager / `finally`),
   or buffered memories are lost and recall scores lie.
2. **Namespace consistency.** The namespace at strategy-creation must match the one at
   retrieval, or it returns nothing, silently. (Default: `semantic/{actorId}`.)
3. **Warm up before timing.** The first invocation after deploy is a cold start;
   discard it before recording latency.
4. **Verify SDK field names against current docs.** The AgentCore Memory SDK evolves;
   don't trust parameter names from memory or old examples.

**Infra:**
- **Memory creation takes ~2–3 min.** `aws_bedrockagentcore_memory.event_expiry_duration`
  is in **days** (7–365; default 90), not an ISO-8601 string.
- **Fresh clone** uses the shared state bucket owned by
  [aws-foundation](../aws-foundation) — apply that repo first, then `terraform init` on
  `infra/`. See [Infrastructure & deploy](#infrastructure--deploy).

---

## How we test

Testing **is** the point — it means *empirically measuring memory behavior*, not unit
testing (there is deliberately no unit suite). For each config: run the fixed probe set,
score recall.

- **Probe set** (`probes/`): fixed `(seed, question, expected)` triples. *seed* plants
  a fact ("I like sushi with tuna"); *question* probes recall later ("what should I
  order?"); *expected* defines correctness. Kept constant (ADR-004).
- **Scoring** (ADR-006): start with **keyword/substring match** of the answer against
  `expected` — cheap, deterministic, transparent. Move to **LLM-as-judge** only if too
  brittle (the judge adds its own error). The method must be **identical across every
  run in a sweep**, or the comparison is meaningless.
- **No-memory baseline** (ADR-007): every sweep includes a control run with memory
  **disabled**. "70% recall" is meaningless until you know it's e.g. "20%" without
  memory. Read every result against this floor.
- **Nondeterminism** (ADR-008): set **temperature = 0** where supported and/or run each
  config **N times and averaging** (record N). Don't report a single lucky number.
- **One parameter first; interactions later.** Single-param sweeps for clean
  attribution; a 2-parameter grid (e.g. top-k × threshold) is a deliberate, clearly
  labeled later step.

The **smoke test** is mock-by-default (free, offline, proves agent wiring + the config
seam); `RUN_LIVE=1` adds a real-Bedrock test (ADR-010).

---

## Infrastructure & deploy

Infra is Terraform in [`infra/`](infra/). **Remote state** lives in a versioned,
encrypted S3 bucket with S3-native locking (`use_lockfile`, no DynamoDB — ADR-012). The
**state bucket and the GitHub OIDC provider are account-wide singletons owned by the
shared [aws-foundation](../aws-foundation) repo** (ADR-014), not by this repo.

**Fresh clone:**

```bash
# 1) once per account: apply aws-foundation (creates/imports the shared bucket + OIDC).
#    See ../aws-foundation/AGENTS.md.
# 2) then, here:
cd infra && terraform init                                 # backend points at the shared bucket
```

> **`infra/bootstrap/` is superseded by aws-foundation** and kept only because
> agent-lab's live state currently sits in `agent-memory-lab-tfstate-...` (which
> aws-foundation now also owns). Don't run it on new clones; remove it once the state
> is consolidated onto the canonical shared bucket.

The CI deploy role lives in the main config ([`infra/cicd.tf`](infra/cicd.tf)), not a
separate folder — it's created by the one-time **bootstrap.yml** workflow (a targeted
apply) and managed by the pipeline thereafter. It *references* the account-wide GitHub
OIDC provider via a data source rather than creating one (only one provider per issuer
URL is allowed per account; the sibling repo shares it).

The state bucket name is deterministic
(`agent-memory-lab-tfstate-<account-id>-<region>`, hardcoded in
[`infra/backend.tf`](infra/backend.tf)); update it if your account/region differ. State
files are git-ignored; only `.tf` config and `.terraform.lock.hcl` are committed.

**The memory resource** ([`infra/memory.tf`](infra/memory.tf)):
`aws_bedrockagentcore_memory` + a `SEMANTIC` `aws_bedrockagentcore_memory_strategy`,
created by the same `terraform apply`. `MEMORY_ID` comes from `terraform output
memory_id`. Verify: `aws bedrock-agentcore-control get-memory --memory-id "$MEMORY_ID"`
→ `status: ACTIVE`.

**Local vs. AgentCore Runtime** — same code, both places: local serves direct calls /
HTTP; the Runtime serves `/ping` + `/invocations` from an ARM64 Docker image in ECR,
pointing at the **same memory resource by ID**. Deploy with `agentcore deploy`; tail
logs with `aws logs tail /aws/bedrock-agentcore/runtimes/<name> --since 1h`.

### CI/CD (GitHub Actions + OIDC)

Two workflows in [`.github/workflows/`](.github/workflows/), modeled on the sibling
[agentcore-multiagent](../agentcore-multiagent) project's OIDC pattern:

- **`bootstrap.yml`** — run **once, manually** (`workflow_dispatch`). Creates the CI
  deploy role with a targeted apply of `infra/cicd.tf` (the role can't create itself
  from inside the pipeline). Needs temporary bootstrap secrets (deleted afterward) and
  prints the role ARN to set as the `AWS_ROLE_ARN` Actions variable. After this, no
  long-lived AWS keys live in GitHub.
- **`deploy.yml`** — on every push/PR: runs the **mocked pytest suite** (`test` job,
  no AWS). On push to **main** only: the `deploy` job assumes `AWS_ROLE_ARN` via OIDC
  and runs `terraform apply` on `infra/`.

Required Actions **variables**: `AWS_REGION`, `GITHUB_REPO` (for bootstrap),
`AWS_ROLE_ARN` (set from bootstrap output). The one-time bootstrap **secrets**
(`AWS_BOOTSTRAP_ACCESS_KEY_ID` / `_SECRET_ACCESS_KEY`) are deleted once the role exists.

### Cost & teardown

**This costs real money.** Bedrock calls scale with sweep size ((values) × (probes) ×
(repeats) + baseline); AgentCore Memory bills storage/retrieval; the Runtime bills
compute + ECR + CloudWatch. **Keep cost down:** small probe set, modest value lists,
deliberate repeat count `N`. **Tear down when done:** delete unused Runtimes, the memory
resource (recreating is cheap), ECR images, and old log groups. Confirm current
Bedrock/AgentCore pricing before large sweeps.

---

## Where things stand — status board

The single source of truth for status. Update this table when an iteration changes
state.

| Iteration | Goal | Status | Notes |
|-----------|------|--------|-------|
| 0 | Project scaffold & docs wiring | ✅ Done | Doc system created (later consolidated into this file). |
| 1 | Minimal local Strands agent | ✅ Done | + Terraform (Bedrock access), AWS CLI verify, verified live on AWS. |
| 2 | Create AgentCore Memory resource | ✅ Done | Terraform memory + semantic strategy; `MEMORY_ID` in env. |
| 3 | Attach memory to the agent | ⬜ Not started | Inject config, one strategy; store a fact, recall it later. |
| 4 | Probe set + scoring | ⬜ Not started | Fixed `(seed, question, expected)`; keyword match; latency. |
| 5 | Sweep harness | ⬜ Not started | Sweep one param, no-memory baseline, emit table/CSV. |
| 6 | Deploy to AgentCore Runtime | ⬜ Not started | `/ping` + `/invocations`, no code change. |
| 7 | First full sweep + writeup | ⬜ Not started | Run, read the table, explain it. |

**Legend:** ⬜ Not started · 🔵 In progress · ✅ Done · ⚠️ Blocked.
**Next up:** Iteration 3 — Attach memory to the agent.

### Definitions of done (the next few iterations)

- **Iter 3:** `memory/` builds an `AgentCoreMemorySessionManager` from a config object;
  agent stores a fact one turn and recalls it later; config injected, not hardcoded;
  session always flushed/closed.
- **Iter 4:** `probes/` holds fixed triples; a scorer judges recall (start with
  keyword/substring); latency captured; scoring identical across runs.
- **Iter 5:** `harness/` runs the full probe set per config; `--sweep <param> --values
  <list>` works for at least `top_k`; no-memory baseline included; nondeterminism
  handled; output table/CSV; exactly one parameter varies.
- **Iter 6:** `/ping` + `/invocations` satisfied; `agentcore deploy` works; same memory
  resource by ID; CloudWatch logs visible.
- **Iter 7:** one parameter swept end-to-end; short writeup explains *why*
  recall/relevance/latency moved.

**Parking lot (not in the plan — don't act silently):** swap embedding models and
re-run; add recency/decay weighting; TypeScript port once the managed Memory module
ships.

---

## Working loop & decision log

**Each session:** orient against the [status board](#where-things-stand--status-board)
and pick the next unchecked iteration → work, following the
[conventions](#conventions-dont-break-these) and [gotchas](#critical-gotchas-read-before-touching-these-areas)
→ tick the box / update the board when state changes → record the change in the git
commit. Keep this file in sync with the code; it is the interface between agents.

**Key decisions (kept here so the rationale survives):**

- **ADR-001 — Python, not TypeScript.** The full Memory system is complete in Python;
  the TS Memory module isn't. A future TS port would hand-build the memory layer.
- **ADR-002 — Inject memory config; never hardcode.** *The* design seam that makes
  sweeping possible. Editing agent logic to change a memory setting is a broken design.
- **ADR-003 — One parameter per sweep.** Clean attribution; results comparable only
  within a single-parameter sweep.
- **ADR-004 — Fixed, small, hand-written probe set.** A teaching instrument, not a
  benchmark. Editing it creates a new baseline.
- **ADR-006 — Scoring: keyword match first, LLM-judge only if needed**, held constant
  across runs.
- **ADR-007 — Always run a no-memory baseline as the control.**
- **ADR-008 — Mitigate LLM nondeterminism** (temperature 0 and/or N repeats averaged).
- **ADR-009 — Provision AWS infra with Terraform** (reproducible, reviewable,
  tear-down-able).
- **ADR-010 — Smoke test is mock-by-default; real Bedrock is opt-in (`RUN_LIVE=1`).**
- **ADR-012 — Terraform state in S3 with native locking**, bootstrapped by a separate
  local-state config.
- **ADR-013 — GitHub Actions auth via OIDC** (no long-lived AWS keys in GitHub).
- **ADR-014 — Account-wide singletons live in a shared `aws-foundation` repo.** The
  GitHub OIDC provider and the shared tfstate bucket are one-per-account and shared by
  every app repo, so they're owned once in [aws-foundation](../aws-foundation); app
  repos only *reference* them. This supersedes the per-repo `infra/github-oidc/` (now
  removed) and `infra/bootstrap/` (now superseded) approaches.

> **History note:** this repo previously kept its guidance split across IDEA / DESIGN /
> DEVELOPMENT / TESTING / DEPLOYMENT / DECISIONS / RESULTS / CHANGELOG `.md` files.
> They were consolidated into this single AGENTS.md (2026-06-22) to match the sibling
> [agentcore-multiagent](../agentcore-multiagent) project's lean docs. Sweep results,
> when they exist, go in a `RESULTS` section here or a `results/` artifact — not a
> separate top-level doc.
