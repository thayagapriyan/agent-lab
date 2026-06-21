# AGENTS.md

The **contract for any agent (AI or human) working in this repo**. This file
follows the `AGENTS.md` convention: the one place that tells a coding agent how to
behave here and where to find everything else. Read it before making changes.

For *how to build/run* the project, see [DEVELOPMENT.md](DEVELOPMENT.md); this file
is about the **working loop and conventions**, not setup.

## What this project is

A Python Strands agent on Amazon Bedrock AgentCore Runtime, plus a harness that
**tests the agent's memory by sweeping parameters**. See [IDEA.md](IDEA.md) for the
concept and [DESIGN.md](DESIGN.md) for the design. The point of the codebase is the
experiment, so changes must preserve the ability to sweep one memory parameter at a
time against a fixed probe set.

> **Start here:** before doing anything, read
> [DEVELOPMENT.md](DEVELOPMENT.md#iterations--status--plan) — the read-first doc
> with the live status board and iteration plan that tell you what to work on next.
> The [documentation map](#documentation-map) below explains how all the `.md` files
> fit together.

## Agent working loop

**Every agent (AI or human) follows this loop, every session.** It is the contract
that keeps the docs in sync with the code so the next agent can pick up cleanly.

1. **Log the request.** Start a new [CHANGELOG.md](CHANGELOG.md) entry capturing the
   user's requirement/request for this session (newest on top).
2. **Orient.** Read [DEVELOPMENT.md → Iterations](DEVELOPMENT.md#iterations--status--plan)
   — find the current iteration and the next unchecked task. Pull context as needed:
   [IDEA.md](IDEA.md) (why), [DESIGN.md](DESIGN.md) (how it's built), the rest of
   [DEVELOPMENT.md](DEVELOPMENT.md) (how to run it).
3. **Pick** the next task in the current iteration (or start the next iteration if
   the current one is done). Set its status to 🔵 In progress in the status board.
4. **Work**, following the conventions and gotchas in
   [DEVELOPMENT.md](DEVELOPMENT.md) and the testing method in
   [TESTING.md](TESTING.md).
5. **Sync the docs** — do not finish with docs out of date. Update the file whose
   job covers what you changed (one fact lives in one file):
   - *Pipeline docs:* Purpose/scope → [IDEA.md](IDEA.md). Design/data flow →
     [DESIGN.md](DESIGN.md). Build/run/conventions **and status/iteration plan** →
     [DEVELOPMENT.md](DEVELOPMENT.md) (always tick the box + update the
     [status board](DEVELOPMENT.md#status-board)). Testing method →
     [TESTING.md](TESTING.md). Deploy / AWS / IAM / cost → [DEPLOYMENT.md](DEPLOYMENT.md).
   - *Tracking docs:* Sweep tables → [RESULTS.md](RESULTS.md). A costly-to-reverse
     choice → an ADR in [DECISIONS.md](DECISIONS.md).
6. **Close out.** Finish the [CHANGELOG.md](CHANGELOG.md) entry describing **how**
   you achieved the goal and which docs changed. At iteration end (or when the user
   stops), make sure [RESULTS.md](RESULTS.md) and [DECISIONS.md](DECISIONS.md)
   reflect what was found and decided.

> **Golden rule:** the docs are the interface between agents. Never leave them out
> of sync with the code at the end of a session. **One fact lives in one file** —
> update it where it lives; don't duplicate it elsewhere.

## The core conventions (don't break these)

Full detail in [DEVELOPMENT.md](DEVELOPMENT.md#conventions); the non-negotiables:

- **Inject memory config; never hardcode it.** All tunable memory settings flow
  through one config object the harness varies. Editing agent logic to change a
  memory setting is the signal you've broken the design — lift it into the config.
- **One parameter per sweep.** Clean attribution; multi-parameter changes make
  results uninterpretable.
- **Keep the probe set fixed.** Don't edit `probes/` to flatter a run; a changed
  probe set is a new baseline — say so loudly.
- **One agent, one session per run.** Don't attach multiple agents to a session.

## Scope guardrails

This is a **learning lab, not production**. Don't add auth hardening, multi-tenancy,
SLAs, or large benchmark suites unless explicitly asked — they work against the
project's purpose: a small, fast, repeatable memory experiment.

## Documentation map

How all the `.md` files are wired together. **One fact lives in one file** — each
doc has a single job and links to the others rather than repeating them. **Keep this
map in sync** if you add or remove a doc.

### Group A — Pipeline (the product docs)

The lifecycle of the work, read in order. A human idea flows down this chain into a
tested, deployed system. **`DEVELOPMENT.md` is the read-first doc** — it also holds
the status board + iteration plan.

```
   IDEA → DESIGN → DEVELOPMENT → TESTING → DEPLOYMENT
   (why)  (how it's (build +    (local &  (ship + AWS
           designed)  status +   smoke)    + cost)
                      plan)
```

| File | Role | Read it when… |
|------|------|----------------|
| [IDEA.md](IDEA.md) | **Why** — the human idea, concept, memory taxonomy, what we measure | You need purpose & scope |
| [DESIGN.md](DESIGN.md) | **How it's designed** — big picture + components, data flow, config seam | You're changing structure or wiring |
| [DEVELOPMENT.md](DEVELOPMENT.md) | **How to build/run + where we are** — stack, setup, commands, conventions, gotchas, **status board + iteration plan** | First, always; before you write code |
| [TESTING.md](TESTING.md) | **How we test** — probes, scoring, baseline, local + smoke, sweeps | You're touching the experiment |
| [DEPLOYMENT.md](DEPLOYMENT.md) | **How to ship** — local vs. Runtime, `agentcore deploy`, plus AWS/IAM/cost/teardown | You're deploying or setting up AWS |

### Group B — Tracking (the process docs)

What we found and why we chose it. Updated as work progresses and at iteration end.
(The status board lives in `DEVELOPMENT.md`; these two are the lasting records.)

| File | Role | Mutability | Read it when… |
|------|------|-----------|----------------|
| [RESULTS.md](RESULTS.md) | **What we found** — sweep tables + interpretation | Append per sweep | You ran a sweep / want findings |
| [DECISIONS.md](DECISIONS.md) | **Why we chose** — ADRs | Append (mark superseded) | Making/revisiting a costly choice |

### Session log & contract

| File | Role |
|------|------|
| [CHANGELOG.md](CHANGELOG.md) | **The session log.** Every user session starts here with the request; records which docs changed as a result. |
| [AGENTS.md](AGENTS.md) (this file) | **The contract.** How any agent should behave; holds this documentation map. |

**Reading order for a new agent:** `DEVELOPMENT.md` (status + plan) → `AGENTS.md`
(this file, the loop) → `IDEA.md` → `DESIGN.md`. Pull `TESTING.md` / `DEPLOYMENT.md`
when the task touches them. Then do the work and write back per the
[agent working loop](#agent-working-loop).

```
   CHANGELOG.md  ── session starts here: log the user's request
        │  drives changes into ▼
        │
   GROUP A · PIPELINE (product)        GROUP B · TRACKING (process)
   ┌──────────────────────────┐        ┌───────────────────────────┐
   │ IDEA → DESIGN →          │        │ RESULTS   (what we found)  │
   │ DEVELOPMENT(status+plan) │◀──────▶│ DECISIONS (why we chose)   │
   │ → TESTING → DEPLOYMENT   │        │                            │
   └──────────────────────────┘        └───────────────────────────┘
        ▲                                       ▲
        └──────────── AGENTS.md ────────────────┘
              (the contract — holds this map)

   At iteration end (or when the user stops):
   update RESULTS.md + DECISIONS.md, finish the CHANGELOG.md entry.
```
