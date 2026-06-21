# CHANGELOG.md

**The session log — the front door of every interaction.** Each user session
starts here: capture the **requirement / request** the user came with, then record
**how** it was addressed and which docs changed. Append-only; this is the project's
memory across sessions, and the audit trail that ties a user request to the changes
it produced across the pipeline docs.

> **The flow:** a user arrives with a description → log it here → make the
> necessary changes to the pipeline docs ([IDEA.md](IDEA.md) →
> [DESIGN.md](DESIGN.md) → [DEVELOPMENT.md](DEVELOPMENT.md) →
> [TESTING.md](TESTING.md) → [DEPLOYMENT.md](DEPLOYMENT.md)) → at iteration end (or
> when the user stops), update [RESULTS.md](RESULTS.md) and
> [DECISIONS.md](DECISIONS.md). This file links the *request* to the *result*.
>
> **Append-only:** add new entries at the top, never rewrite or delete old ones.
> For live status and the plan, see
> [DEVELOPMENT.md → Iterations](DEVELOPMENT.md#iterations--status--plan). For how the
> docs fit together, see the [documentation map](AGENTS.md#documentation-map).

## How to add an entry

- **Start each session** by adding an entry with the user's **requirement /
  request** before doing the work; fill the rest as you go.
- Put the **newest entry at the top** (reverse-chronological).
- Reference the iteration number from
  [DEVELOPMENT.md → Iterations](DEVELOPMENT.md#iterations--status--plan).
- Record decisions, surprises, and gotchas — that is what helps the next agent.
- Use absolute dates (`YYYY-MM-DD`), not "today" or "yesterday".

### Entry template

```markdown
## [YYYY-MM-DD] Iteration N — <short title>

**Requirement / request:** <what the user asked for this session, in their terms>
**Goal:** <the iteration goal, copied from DEVELOPMENT.md>
**Status after this entry:** <In progress | Done | Blocked>
**Agent:** <model/name or human>

**What changed:**
- <files/components added or modified, and why>

**How the goal was achieved:**
- <the approach — key steps, the path taken>

**Decisions & trade-offs:**
- <choices made and why; alternatives rejected — promote durable ones to DECISIONS.md>

**Gotchas / surprises:**
- <anything that bit you or the next agent should know>

**Docs updated:**
- <which .md files were changed to stay in sync — pipeline and/or tracking docs>

**Next:**
- <what the following agent should pick up>
```

---

## [2026-06-21] Iteration 1 — verified live against AWS + repo hygiene

**Requirement / request:** "I merged Iteration 1 to main. How do I test it now?" —
user wanted to test Terraform + the agent against their **real AWS account** (not
offline mocks).
**Goal:** Prove Iteration 1 end to end on real AWS, and fix what the test surfaced.
**Status after this entry:** Done
**Agent:** Claude (Opus 4.8)

**What changed:**
- **Verified live:** `aws sts get-caller-identity` (account 224193574799),
  `verify_bedrock.sh` OK, `terraform apply` created the IAM role + scoped policy,
  and `agent.serve` did a real Bedrock round trip ("pong"); `RUN_LIVE=1` pytest
  passed. Full suite still 4 passed / 1 skipped.
- **Default model id changed** to `us.anthropic.claude-haiku-4-5-20251001-v1:0`
  (the prior default wasn't in the account; `claude-3-haiku` is Legacy/blocked).
  Updated `config.py`, `.env.example`, `infra/variables.tf`.
- **IAM policy now handles inference profiles** (`infra/iam.tf`): allows InvokeModel
  on both the `inference-profile/...` ARN and underlying `foundation-model/...` ARNs.
- **Fixed doubled CLI output** (`core.py`: `callback_handler=None`).
- **Auto-load `.env`** via optional `python-dotenv` (`config.py`, `requirements.txt`).
- **Repo hygiene:** untracked `infra/.terraform/` (provider plugin) and all
  `__pycache__/*.pyc` that a prior commit had added; `.gitignore` now keeps
  `.terraform.lock.hcl` tracked (Terraform best practice) and ignores `**/.terraform/`.
- Documented the Bedrock gotchas (inference profile, Legacy models, IAM breadth) in
  `DEVELOPMENT.md`.

**How the goal was achieved:**
- Used the AWS CLI to discover which models/inference profiles were actually ACTIVE
  in the account, switched to one, fixed the IAM policy to match, then confirmed a
  real round trip and the gated live test.

**Decisions & trade-offs:**
- Track `.terraform.lock.hcl` (pins provider versions) but never the provider
  binaries or local state.
- Kept `python-dotenv` optional (graceful fallback) so real env vars still work.

**Gotchas / surprises:**
- Newer Claude models require the `us.`-prefixed inference profile id, not the bare
  model id. `claude-3-haiku` is Legacy and blocked for inactive accounts.
- A prior commit had tracked `.terraform/` provider files and `.pyc` despite
  `.gitignore` (they were added before the ignore rule / via merge). Cleaned up.

**Docs updated:**
- `DEVELOPMENT.md` (gotchas), `CHANGELOG.md`. Code/infra: `agent/config.py`,
  `agent/core.py`, `infra/iam.tf`, `infra/variables.tf`, `requirements.txt`,
  `.env.example`, `.gitignore`.

**Next:**
- Iteration 2 — Create the AgentCore Memory resource (extend `infra/`; capture
  `MEMORY_ID`).

---

## [2026-06-21] Doc structure — folded ITERATION.md into DEVELOPMENT.md

**Requirement / request:** "We don't need ITERATION.md — replace it with
DEVELOPMENT.md, because DEVELOPMENT.md should take care of every iteration. Agents
are still referring to ITERATION.md."
**Goal:** Eliminate ITERATION.md; DEVELOPMENT.md becomes the read-first doc that
owns the status board + iteration plan.
**Status after this entry:** Done
**Agent:** Claude (Opus 4.8)

**What changed:**
- Moved the **status board + iteration plan + parking lot** from `ITERATION.md` into
  `DEVELOPMENT.md` (new "Iterations — status & plan" section; jump-links added to
  the header). `DEVELOPMENT.md` is now the read-first doc.
- Moved the **documentation map** into `AGENTS.md` (the contract that references all
  docs), per the user's choice.
- **Deleted `ITERATION.md`.**
- Repointed every live `ITERATION.md` / `ITERATION.md#documentation-map` link across
  `IDEA.md`, `DESIGN.md`, `TESTING.md`, `DEPLOYMENT.md`, `RESULTS.md`, `DECISIONS.md`,
  and the CHANGELOG header to `DEVELOPMENT.md#iterations--status--plan` or
  `AGENTS.md#documentation-map`.
- Updated the working loop in `AGENTS.md` (orient via DEVELOPMENT.md; status updates
  go to its board).

**How the goal was achieved:**
- Confirmed with the user where the doc map should live (AGENTS.md), then moved
  content (not copied), deleted the file, and grepped repo-wide to repair all live
  links. Historical CHANGELOG entries keep their original `ITERATION.md` references
  (append-only); the one dangling link in the oldest entry was un-linked to text.

**Decisions & trade-offs:**
- Recorded as **ADR-011** (iterations in DEVELOPMENT.md, map in AGENTS.md), which
  supersedes the ITERATION.md placement noted in ADR-005.
- Trade-off: DEVELOPMENT.md is longer now; mitigated with jump-links and clear
  section headers. Tracking group shrinks to RESULTS ↔ DECISIONS.

**Gotchas / surprises:**
- Many cross-links pointed at `ITERATION.md#documentation-map`; all repaired.

**Docs updated:**
- Deleted: `ITERATION.md`. Edited: `DEVELOPMENT.md`, `AGENTS.md`, `IDEA.md`,
  `DESIGN.md`, `TESTING.md`, `DEPLOYMENT.md`, `RESULTS.md`, `DECISIONS.md`
  (ADR-005 note + ADR-011), `CHANGELOG.md`.

**Next:**
- Iteration 2 — Create the AgentCore Memory resource.

---

## [2026-06-21] Iteration 1 — Minimal local Strands agent

**Requirement / request:** Start Iteration 1. User wants the smoke test to use the
AWS CLI for verification and to add **Terraform** to provision the necessary AWS
changes (Bedrock access only for now).
**Goal:** A Strands agent that answers a prompt locally, no memory yet.
**Status after this entry:** Done
**Agent:** Claude (Opus 4.8)

**What changed:**
- `agent/` package: `config.py` (`AgentConfig` from `AWS_REGION` /
  `BEDROCK_MODEL_ID`), `core.py` (`build_agent`, `run_once`, and a `build_model`
  factory seam), `serve.py` (local CLI: `python -m agent.serve "prompt"`).
- `infra/` Terraform (Bedrock access only): provider, IAM role + scoped
  `bedrock:InvokeModel` policy, variables, outputs, `terraform.tfvars.example`.
- `scripts/verify_bedrock.sh` — AWS CLI check of model availability (no invoke).
- `tests/test_smoke.py` — mock round-trip + config tests (default), live Bedrock
  test gated behind `RUN_LIVE=1`.
- `.gitignore`, `requirements.txt`, `.env.example`.

**How the goal was achieved:**
- Built the agent behind a model factory so the same code runs against real
  Bedrock or an injected mock. Created a venv, installed `requirements.txt`, and
  ran the suite: **4 passed, 1 skipped** (live test skipped without `RUN_LIVE`).
- Verified the real SDK API names used (`strands.Agent`,
  `strands.models.BedrockModel`) against the installed package — not guessed.
- `terraform validate` passes (fixed one provider-5.x deprecation:
  `aws_region.name` → `.region`); `terraform fmt` applied.

**Decisions & trade-offs:**
- **Terraform** for infra (ADR-009) and **mock-default / `RUN_LIVE` opt-in** smoke
  testing with an AWS CLI verifier (ADR-010) — both per user request.
- Iteration 1 Terraform scope kept minimal: **Bedrock access only**; memory / ECR /
  Runtime deferred to their iterations.

**Gotchas / surprises:**
- Local Python is 3.14 (docs floor is 3.10+ — fine).
- Global interpreter had no pytest; created `.venv` and installed deps there.
- AWS provider 5.x deprecates `data.aws_region.current.name` → use `.region`.

**Docs updated:**
- `DESIGN.md` (Agent Service now implemented + model-factory seam),
  `DEVELOPMENT.md` (real setup/layout/commands), `DEPLOYMENT.md` (Terraform infra +
  AWS CLI verify), `DECISIONS.md` (ADR-009, ADR-010), `ITERATION.md` (DoD ticked,
  status board), `CHANGELOG.md`.

**Next:**
- Iteration 2 — Create the AgentCore Memory resource (extend `infra/` with the
  memory resource; capture `MEMORY_ID`).

---

## [2026-06-21] Iteration 0 (follow-up) — Consolidated to a two-group lifecycle layout

**Requirement / request:** User wants a solid, lasting way to arrange the `.md`
files for both humans and agents: delete `ARCHITECTURE.md` (fold into `DESIGN.md`);
fold `INFRASTRUCTURE.md` into `DEPLOYMENT.md`; treat the docs as a lifecycle
pipeline (IDEA → DESIGN → DEVELOPMENT → TESTING → DEPLOYMENT) interlinked with a
tracking group (ITERATION ↔ RESULTS ↔ DECISIONS); make `CHANGELOG.md` the
per-session log that starts each interaction; `AGENTS.md` references all.
**Goal:** Reorganize the doc system into the two-group model above.
**Status after this entry:** Done
**Agent:** Claude (Opus 4.8)

**What changed:**
- **Deleted `ARCHITECTURE.md`** — its overview + diagram folded into the top of
  `DESIGN.md` (now the single design doc).
- **Deleted `INFRASTRUCTURE.md`** — its content folded into `DEPLOYMENT.md` as
  "Part 1 — Infrastructure" and "Part 3 — Cost & teardown".
- Added consistent **pipeline navigation** (◀ prev / next ▶) to all five Group A
  docs so IDEA→DESIGN→DEVELOPMENT→TESTING→DEPLOYMENT is walkable.
- **Reframed `CHANGELOG.md`** as the session log: the request is captured at
  session start; added a "Requirement / request" field to the entry template.
- Rewrote `AGENTS.md`: a "How the docs are organized" section (two groups + session
  log), a working loop that now starts by logging the request, and a regrouped
  "where everything lives" index.
- Rebuilt the **documentation map** in `ITERATION.md` around Group A (Pipeline),
  Group B (Tracking), the session log, and the contract — with a new diagram.
- Fixed all live cross-links that pointed at the deleted files (`DESIGN.md`,
  `DEVELOPMENT.md`, `DECISIONS.md`, `ITERATION.md`).

**How the goal was achieved:**
- Resolved a contradiction in the request (whether `ITERATION.md` merges into
  `DEVELOPMENT.md`): confirmed with the user it was a slip for `CHANGELOG.md`, so
  `ITERATION.md` stays standalone in the tracking group.
- Moved (not copied) content so each fact still lives in exactly one file, then
  re-linked everything. Net file count: 12 → 10.

**Decisions & trade-offs:**
- Folding infra into `DEPLOYMENT.md` keeps the pipeline to five clean stages, at the
  cost of a longer deployment doc (mitigated with Part 1/2/3 structure).
- Kept `AGENTS.md` (auto-detected convention) and `ITERATION.md` standalone.

**Gotchas / surprises:**
- Historical CHANGELOG entries still name the deleted files — left intact on purpose
  (append-only history must reflect what was true then).

**Docs updated:**
- Deleted: `ARCHITECTURE.md`, `INFRASTRUCTURE.md`. Edited: `DESIGN.md`,
  `DEPLOYMENT.md`, `IDEA.md`, `DEVELOPMENT.md`, `TESTING.md`, `DECISIONS.md`,
  `AGENTS.md`, `ITERATION.md`, `CHANGELOG.md`.

**Next:**
- Iteration 1 — minimal local Strands agent. (Docs are now stable; time to write
  code so they don't drift ahead of reality.)

---

## [2026-06-21] Iteration 0 (follow-up) — Adopted traditional delivery-doc layout

**Goal:** Restructure the docs into the conventional software layout (DESIGN /
DEVELOPMENT / TESTING / DEPLOYMENT / INFRASTRUCTURE) so both developers and agents
navigate effectively — by *moving* content, not duplicating it.
**Status after this entry:** Done
**Agent:** Claude (Opus 4.8)

**What changed:**
- Added 5 delivery docs by carving content out of the two big files:
  - `DESIGN.md` ← detailed design from `ARCHITECTURE.md`; **added** "one app, many
    configs" and "build once, run many" sections (the gap the user flagged).
  - `DEVELOPMENT.md` ← stack, setup, layout, commands, conventions, gotchas from
    `AGENTS.md`.
  - `TESTING.md` ← experiment method (probes, scoring, baseline, nondeterminism,
    running a sweep), drawing the operational detail out of `IDEA.md`.
  - `DEPLOYMENT.md` ← deployment section from `ARCHITECTURE.md`.
  - `INFRASTRUCTURE.md` ← env values + **new** AWS account / IAM / cost & teardown
    content (previously under-documented).
- Thinned `ARCHITECTURE.md` to a one-screen **overview hub** that links to the
  delivery docs.
- Thinned `AGENTS.md` to the **agent contract**: the working loop, core
  conventions, scope guardrails, and a "where everything lives" index. Setup/
  commands moved to `DEVELOPMENT.md`.
- Rebuilt the **documentation map** in `ITERATION.md` (now grouped: Process spine /
  Context & delivery / Outputs) with a new wiring diagram and reading order.
- Fixed stale anchors (`ARCHITECTURE.md#...`, `AGENTS.md#setup`) to point at the
  moved content in `DESIGN.md` / `DEVELOPMENT.md`.

**How the goal was achieved:**
- Per the user's steer, *moved* (not copied) content so each fact lives in exactly
  one file, then back-linked everything. Kept `ARCHITECTURE.md` and `AGENTS.md`
  names (both are recognized conventions; AGENTS.md is auto-detected by AI tools)
  but reduced them to hub/contract roles.

**Decisions & trade-offs:**
- Chose "thin to hubs" over deleting `ARCHITECTURE.md`/`AGENTS.md`, preserving the
  conventions while still getting the traditional layout.
- Net doc count is higher (12 files) but each has one job and no duplication —
  enforced by the "one fact lives in one file" rule now stated in `AGENTS.md` and
  the doc map.

**Gotchas / surprises:**
- Two cross-links pointed into sections that moved; caught and repaired.

**Docs updated:**
- New: `DESIGN.md`, `DEVELOPMENT.md`, `TESTING.md`, `DEPLOYMENT.md`,
  `INFRASTRUCTURE.md`. Edited: `ARCHITECTURE.md`, `AGENTS.md`, `ITERATION.md`,
  `DECISIONS.md`, `CHANGELOG.md`.

**Next:**
- Iteration 1 — minimal local Strands agent.

---

## [2026-06-21] Iteration 0 (follow-up) — Made testable scope explicit in the taxonomy

**Goal:** Clarify which memory-taxonomy concepts the lab can actually *sweep* vs.
which are explained for context only.
**Status after this entry:** Done
**Agent:** Claude (Opus 4.8)

**What changed:**
- Reworked the taxonomy table in `IDEA.md`: added a **"Tested in this lab?"**
  column with clear tags (Swept core / Swept one-knob / Used not swept /
  Constraint / Stretch) and a "How / which knob" column. Reordered most-tested
  first.
- Added a one-line **scope summary**: fully sweep the long-term/RAG layer (4
  knobs), sweep short-term with one knob, treat session/context-window/embeddings
  as context, not dials.
- Added a **Layer** column to the "Parameters under test" table so every knob ties
  back to a taxonomy concept (the two tables now cross-reference).

**How the goal was achieved:**
- Mapped each of the 6 taxonomy concepts to the parameter table and found 3 are
  not sweepable (context window = fixed limit; session memory = on/off, no dial;
  embedding = stretch). Surfaced that explicitly instead of leaving readers to
  infer it.

**Decisions & trade-offs:**
- Kept the full 6-concept taxonomy (educational value) but labeled scope, rather
  than trimming the taxonomy or expanding the project with costlier sweeps.

**Gotchas / surprises:**
- The taxonomy implied all six concepts were tunable; only four have dials. Now
  unambiguous.

**Docs updated:**
- `IDEA.md`, `CHANGELOG.md`.

**Next:**
- Iteration 1 — minimal local Strands agent.

---

## [2026-06-21] Iteration 0 (follow-up) — Memory taxonomy + experiment design

**Goal:** Close conceptual gaps in the project idea: define the memory vocabulary
and make the experiment methodology sound.
**Status after this entry:** Done
**Agent:** Claude (Opus 4.8)

**What changed:**
- Added a **Memory taxonomy** section to `IDEA.md` defining context window,
  short-term, session, long-term memory, retrieval/RAG, and embeddings — with a
  mental-model diagram and an explicit "is this RAG?" note. These terms were
  previously scattered and undefined across the docs.
- Added an **Experiment design** section to `IDEA.md` covering the four gaps:
  scoring method, a no-memory baseline (control), nondeterminism handling, and
  single-param-first / interactions-later.
- Added ADR-006 (scoring method), ADR-007 (no-memory baseline), ADR-008
  (nondeterminism) to `DECISIONS.md`.
- Wired the new concerns into Iteration 4 (scoring) and Iteration 5 (baseline,
  repeats, write to RESULTS.md) in `ITERATION.md`.

**How the goal was achieved:**
- Grepped all docs for the memory terms and found they were implicit only (RAG
  absent entirely; short/long-term mentioned once with no definition). Wrote a
  single authoritative taxonomy in `IDEA.md`, then captured the experiment-design
  decisions as ADRs so they bind future work.

**Decisions & trade-offs:**
- Framed the project explicitly as an *experiment*, not just an engineering task —
  hence the control baseline and nondeterminism handling now being first-class.
- Kept scoring deliberately simple to start (keyword match) to stay deterministic;
  LLM-judge deferred until simple proves insufficient.

**Gotchas / surprises:**
- "RAG" appeared nowhere despite AgentCore Memory being a managed RAG system — the
  biggest conceptual gap. Now addressed directly.

**Docs updated:**
- `IDEA.md`, `DECISIONS.md`, `ITERATION.md`, `CHANGELOG.md`.

**Next:**
- Iteration 1 — minimal local Strands agent.

---

## [2026-06-21] Iteration 0 (follow-up) — Added DECISIONS.md & RESULTS.md

**Goal:** Round out the doc system with a reasoning log and a results home.
**Status after this entry:** Done
**Agent:** Claude (Opus 4.8)

**What changed:**
- Added `DECISIONS.md` — lightweight ADR log, seeded with 5 decisions already
  implied by the existing docs (Python over TS, inject config, one param/sweep,
  fixed probe set, two-file docs split).
- Added `RESULTS.md` — templated shell for sweep tables; empty until Iteration 5
  produces the first sweep. Includes a commented example table.
- Wired both into the documentation map (table + diagram) in `ITERATION.md`, and
  into the agent working loop in `ITERATION.md` and `AGENTS.md`.

**How the goal was achieved:**
- Recommended a conservative set of additions to avoid doc sprawl; user picked
  `DECISIONS.md` and `RESULTS.md`. Created both, then back-linked them everywhere
  so the wiring stays complete.

**Decisions & trade-offs:**
- Kept `RESULTS.md` as an empty shell rather than fabricating numbers — it fills
  from real sweeps. Captured the doc-split rationale as ADR-005.
- Declined README/CONTRIBUTING/ROADMAP/GLOSSARY for now (would duplicate existing
  docs or split status).

**Gotchas / surprises:**
- None.

**Docs updated:**
- `DECISIONS.md` (new), `RESULTS.md` (new), `ITERATION.md`, `AGENTS.md`,
  `CHANGELOG.md`.

**Next:**
- Iteration 1 — minimal local Strands agent.

---

## [2026-06-21] Iteration 0 — Project scaffold & docs wiring

**Goal:** Establish the documentation system so future agents can self-orient.
**Status after this entry:** Done
**Agent:** Claude (Opus 4.8)

**What changed:**
- Added `ITERATION.md` — the live status board + iteration plan (read-first doc).
- Added `CHANGELOG.md` (this file) — append-only history of iterations.
- Cross-linked all `.md` files and added a **documentation map** so the wiring is
  explicit in `ITERATION.md`.
- Extended `AGENTS.md` with the mandatory **agent working loop** (read
  `ITERATION.md` → work → sync all docs → append `CHANGELOG.md`).
- Added a short "Documentation map" pointer to `IDEA.md`, `ARCHITECTURE.md`, and
  `AGENTS.md` so every file points back to the system.

**How the goal was achieved:**
- Read the three existing docs (`IDEA.md`, `ARCHITECTURE.md`, `AGENTS.md`) to
  understand the project, then defined the missing execution layer: a mutable
  status board (`ITERATION.md`) and an immutable history (`CHANGELOG.md`).
- Broke the work into 8 small iterations (0–7), each with a goal, a definition of
  done, and a task checklist.

**Decisions & trade-offs:**
- Chose a **two-file split** (status vs. history) over one combined file, so the
  status board stays short and the history stays honest and append-only.
- Kept the iteration breakdown aligned to the architecture's components
  (agent → memory → probes → harness → deploy) so the plan maps cleanly onto the
  design.

**Gotchas / surprises:**
- None — greenfield docs.

**Docs updated:**
- `ITERATION.md` (new), `CHANGELOG.md` (new), `AGENTS.md`, `IDEA.md`,
  `ARCHITECTURE.md`.

**Next:**
- Iteration 1 — build the minimal local Strands agent. *(At the time this pointed
  to `ITERATION.md`, since merged into DEVELOPMENT.md — see ADR-011.)*
