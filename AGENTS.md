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

> **Start here:** before doing anything, read [ITERATION.md](ITERATION.md) — the
> live status board that tells you what to work on next. The
> [documentation map](ITERATION.md#documentation-map) explains how all the `.md`
> files fit together.

## How the docs are organized

The docs fall into two interlinked groups, plus this file which references both:

- **Pipeline (the product docs)** — the lifecycle of the work, in order:
  [IDEA.md](IDEA.md) → [DESIGN.md](DESIGN.md) → [DEVELOPMENT.md](DEVELOPMENT.md) →
  [TESTING.md](TESTING.md) → [DEPLOYMENT.md](DEPLOYMENT.md). A human idea flows down
  this chain into a deployed, tested system.
- **Tracking (the process docs)** — [ITERATION.md](ITERATION.md) ↔
  [RESULTS.md](RESULTS.md) ↔ [DECISIONS.md](DECISIONS.md): what to do, what we
  found, and why we chose what we chose.
- **Session log** — [CHANGELOG.md](CHANGELOG.md): every user session starts here
  with the request, and it records which pipeline/tracking docs changed as a result.

## Agent working loop

**Every agent (AI or human) follows this loop, every session.** It is the contract
that keeps the docs in sync with the code so the next agent can pick up cleanly.

1. **Log the request.** Start a new [CHANGELOG.md](CHANGELOG.md) entry capturing the
   user's requirement/request for this session (newest on top).
2. **Orient.** Read [ITERATION.md](ITERATION.md) — find the current iteration and
   the next unchecked task. Pull context as needed: [IDEA.md](IDEA.md) (why),
   [DESIGN.md](DESIGN.md) (how it's built), [DEVELOPMENT.md](DEVELOPMENT.md) (how to
   run it).
3. **Pick** the next task in the current iteration (or start the next iteration if
   the current one is done). Set its status to 🔵 In progress in the status board.
4. **Work**, following the conventions and gotchas in
   [DEVELOPMENT.md](DEVELOPMENT.md) and the testing method in
   [TESTING.md](TESTING.md).
5. **Sync the docs** — do not finish with docs out of date. Update the file whose
   job covers what you changed (one fact lives in one file):
   - *Pipeline docs:* Purpose/scope → [IDEA.md](IDEA.md). Design/data flow →
     [DESIGN.md](DESIGN.md). Build/run/conventions → [DEVELOPMENT.md](DEVELOPMENT.md).
     Testing method → [TESTING.md](TESTING.md). Deploy / AWS / IAM / cost →
     [DEPLOYMENT.md](DEPLOYMENT.md).
   - *Tracking docs:* Status/progress → [ITERATION.md](ITERATION.md#status-board)
     (always: tick the box, update the board). Sweep tables → [RESULTS.md](RESULTS.md).
     A costly-to-reverse choice → an ADR in [DECISIONS.md](DECISIONS.md).
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

## Where everything lives

| Need | File | Group |
|------|------|-------|
| What to work on next / status | [ITERATION.md](ITERATION.md) | Tracking |
| Sweep results | [RESULTS.md](RESULTS.md) | Tracking |
| Why decisions were made (ADRs) | [DECISIONS.md](DECISIONS.md) | Tracking |
| Why the project exists + memory taxonomy | [IDEA.md](IDEA.md) | Pipeline |
| The design (big picture + detail) | [DESIGN.md](DESIGN.md) | Pipeline |
| Setup, commands, conventions, gotchas | [DEVELOPMENT.md](DEVELOPMENT.md) | Pipeline |
| How we test memory (local + smoke) | [TESTING.md](TESTING.md) | Pipeline |
| Deploy + AWS, IAM, cost, teardown | [DEPLOYMENT.md](DEPLOYMENT.md) | Pipeline |
| This session's request + history | [CHANGELOG.md](CHANGELOG.md) | Session log |
| How to behave here (this file) | [AGENTS.md](AGENTS.md) | Meta |
