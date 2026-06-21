# ITERATION.md

**The single source of truth for project status.** If you are an agent (AI or
human) picking up this project, **read this file first**. It tells you where the
project is, what is done, what is in progress, and what to do next.

> This file is **mutable** — it is a living status board. Edit it as work
> progresses. For the immutable record of *what was done and how*, see
> [CHANGELOG.md](CHANGELOG.md).

See [the documentation map](#documentation-map) at the bottom for how all the
`.md` files fit together.

---

## How to use this file (for every agent)

Follow this loop on **every** session. The full version of these rules lives in
[AGENTS.md](AGENTS.md#agent-working-loop); this is the short form.

1. **Read** this file top to bottom. Identify the current iteration and the next
   unchecked task.
2. **Pick** the next task in the current iteration (or the next iteration if the
   current one is complete).
3. **Do** the work, following the conventions in [AGENTS.md](AGENTS.md) and the
   build/run detail in [DEVELOPMENT.md](DEVELOPMENT.md).
4. **Update the docs** as you go — update the file whose job covers what changed
   (one fact lives in one file):
   - Tick the checkbox here and update the **Status board** below (always).
   - Pipeline: Purpose/scope → [IDEA.md](IDEA.md). Design → [DESIGN.md](DESIGN.md).
     Build/run → [DEVELOPMENT.md](DEVELOPMENT.md). Testing → [TESTING.md](TESTING.md).
     Deploy / AWS / cost → [DEPLOYMENT.md](DEPLOYMENT.md).
   - Tracking: Results → [RESULTS.md](RESULTS.md). Costly choice → an ADR in
     [DECISIONS.md](DECISIONS.md).
5. **Record** what you did in [CHANGELOG.md](CHANGELOG.md) — the session log; one
   entry per session/iteration describing *how* you achieved the goal. If you ran a
   sweep, add the table to [RESULTS.md](RESULTS.md).

> **Golden rule:** never finish a session leaving the docs out of sync with the
> code. The docs are the interface between agents.

---

## Status board

Update this table whenever an iteration changes state.

| Iteration | Goal | Status | Notes |
|-----------|------|--------|-------|
| 0 | Project scaffold & docs wiring | ✅ Done | This doc system created. |
| 1 | Minimal local Strands agent | ⬜ Not started | Runs locally, no memory yet. |
| 2 | Create AgentCore Memory resource | ⬜ Not started | Setup script + IDs in env. |
| 3 | Attach memory to the agent | ⬜ Not started | Inject config, one strategy. |
| 4 | Probe set + scoring | ⬜ Not started | Fixed (seed, question, expected). |
| 5 | Sweep harness | ⬜ Not started | Sweep one param, emit table/CSV. |
| 6 | Deploy to AgentCore Runtime | ⬜ Not started | `/ping` + `/invocations`, no code change. |
| 7 | First full sweep + writeup | ⬜ Not started | Run, read the table, explain it. |

**Status legend:** ⬜ Not started · 🔵 In progress · ✅ Done · ⚠️ Blocked

**Currently in progress:** _none_
**Next up:** Iteration 1 — Minimal local Strands agent.

---

## Iterations

Each iteration is a small, shippable slice. It has a **goal**, a **definition of
done** (so any agent knows when to stop), and a **task checklist**. Keep
iterations small enough to finish and document in one sitting.

> The plan below is the roadmap. Refine it as you learn — but if you change an
> iteration's goal or scope, say so in [CHANGELOG.md](CHANGELOG.md) so the
> history stays honest.

### Iteration 0 — Project scaffold & docs wiring ✅

**Goal:** Establish the documentation system so future agents can self-orient.

**Done when:**
- [x] `ITERATION.md` exists with a status board and iteration plan.
- [x] `CHANGELOG.md` exists and is ready for append-only entries.
- [x] Every `.md` file links to the others (documentation map).
- [x] `AGENTS.md` describes the mandatory agent working loop.

### Iteration 1 — Minimal local Strands agent ⬜

**Goal:** A Strands agent that answers a prompt locally, no memory yet.

**Done when:**
- [ ] `agent/` package with a Strands `Agent` and a Bedrock model.
- [ ] Runs locally (`python -m agent.serve` or direct call) and returns a reply.
- [ ] Model ID and region read from env vars (no hardcoding).
- [ ] A smoke test confirms a prompt → response round trip.

**Notes / pointers:** see [DESIGN.md](DESIGN.md#1-agent-service) and the env vars
in [DEVELOPMENT.md](DEVELOPMENT.md#setup).

### Iteration 2 — Create AgentCore Memory resource ⬜

**Goal:** A managed memory resource exists and its ID is available to the agent.

**Done when:**
- [ ] `scripts/` has a one-time setup that creates the memory resource.
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
- [ ] Output is a side-by-side table / CSV (recall, relevance, latency), written
      to [RESULTS.md](RESULTS.md).
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
- [ ] Findings appended to [CHANGELOG.md](CHANGELOG.md).

---

## Parking lot

Ideas and follow-ups that are **not** in the current plan. Pull them into a real
iteration when ready; don't act on them silently. (See stretch ideas in
[IDEA.md](IDEA.md#stretch-ideas-later-not-now).)

- Swap embedding models and re-run the sweep.
- Add recency/decay weighting; measure effect on old vs. new facts.
- TypeScript port once the managed Memory module ships.

---

## Documentation map

How all the `.md` files are wired together. **One fact lives in one file** — each
doc has a single job and links to the others rather than repeating them. The docs
fall into **two interlinked groups**, plus a session log and the agent contract.
**Keep this map in sync** if you add or remove a doc.

### Group A — Pipeline (the product docs)

The lifecycle of the work, read in order. A human idea flows down this chain into a
tested, deployed system.

```
   IDEA → DESIGN → DEVELOPMENT → TESTING → DEPLOYMENT
   (why)  (how it's (how to     (local &  (ship + AWS
           designed)  build)     smoke)    + cost)
```

| File | Role | Read it when… |
|------|------|----------------|
| [IDEA.md](IDEA.md) | **Why** — the human idea, concept, memory taxonomy, what we measure | You need purpose & scope |
| [DESIGN.md](DESIGN.md) | **How it's designed** — big picture + components, data flow, config seam (absorbed ARCHITECTURE) | You're changing structure or wiring |
| [DEVELOPMENT.md](DEVELOPMENT.md) | **How to build/run** — stack, setup, commands, conventions, gotchas | Before you write code |
| [TESTING.md](TESTING.md) | **How we test** — probes, scoring, baseline, local + smoke, sweeps | You're touching the experiment |
| [DEPLOYMENT.md](DEPLOYMENT.md) | **How to ship** — local vs. Runtime, `agentcore deploy`, plus AWS/IAM/cost/teardown (absorbed INFRASTRUCTURE) | You're deploying or setting up AWS |

### Group B — Tracking (the process docs)

What to do, what we found, why we chose it. Interlinked; updated as work progresses
and at iteration end.

| File | Role | Mutability | Read it when… |
|------|------|-----------|----------------|
| [ITERATION.md](ITERATION.md) (this file) | **Where we are** — status board + iteration plan | Every session | First, always |
| [RESULTS.md](RESULTS.md) | **What we found** — sweep tables + interpretation | Append per sweep | You ran a sweep / want findings |
| [DECISIONS.md](DECISIONS.md) | **Why we chose** — ADRs | Append (mark superseded) | Making/revisiting a costly choice |

### Session log & contract

| File | Role |
|------|------|
| [CHANGELOG.md](CHANGELOG.md) | **The session log.** Every user session starts here with the request; records which docs changed as a result. |
| [AGENTS.md](AGENTS.md) | **The contract.** How any agent should behave; references both groups when needed. |

**Reading order for a new agent:** `ITERATION.md` (here) → `AGENTS.md` → `IDEA.md`
→ `DESIGN.md` (+ `DEVELOPMENT.md` before coding). Pull `TESTING.md` /
`DEPLOYMENT.md` when the task touches them. Then do the work and write back per the
[agent working loop](AGENTS.md#agent-working-loop).

```
   CHANGELOG.md  ── session starts here: log the user's request
        │  drives changes into ▼
        │
   GROUP A · PIPELINE (product)        GROUP B · TRACKING (process)
   ┌──────────────────────────┐        ┌───────────────────────────┐
   │ IDEA → DESIGN →          │        │ ITERATION  (status + plan) │
   │ DEVELOPMENT → TESTING →  │◀──────▶│ RESULTS    (what we found) │
   │ DEPLOYMENT               │        │ DECISIONS  (why we chose)  │
   └──────────────────────────┘        └───────────────────────────┘
        ▲                                       ▲
        └──────────── AGENTS.md ────────────────┘
              (the contract — refers to both groups)

   At iteration end (or when the user stops):
   update RESULTS.md + DECISIONS.md, finish the CHANGELOG.md entry.
```
