# TESTING.md

How we test the agent's memory — the experiment method. Testing *is* the point of
this project, so this doc is central, not an afterthought. It covers the probe set,
how answers are scored, the control baseline, how nondeterminism is handled, and
how a sweep is run.

> ◀ Pipeline: [IDEA.md](IDEA.md) → [DESIGN.md](DESIGN.md) →
> [DEVELOPMENT.md](DEVELOPMENT.md) → **TESTING.md** → [DEPLOYMENT.md](DEPLOYMENT.md)
> ▶. Covers local + smoke testing of memory behavior. Why we measure →
> [IDEA.md](IDEA.md); results land in [RESULTS.md](RESULTS.md). Full map:
> [documentation map](AGENTS.md#documentation-map).

## What "testing" means here

This is not unit testing (there is deliberately no unit-test suite — see scope
guardrails in [DEVELOPMENT.md](DEVELOPMENT.md)). "Testing" means **empirically
measuring memory behavior**: run a fixed set of probes against the agent under a
given memory config, and score how well it remembered.

A **run** = (one config) × (the fixed probe set). Sweep one parameter, hold the
rest, record the scores, compare.

## What we measure

For each configuration:

- **Recall accuracy** — did the agent correctly remember the probed fact?
- **Relevance** — were retrieved memories on-topic for the question?
- **Latency** — wall-clock time per turn.

## The probe set

A fixed, hand-written set of `(seed, question, expected)` triples, living in
`probes/`:

- **seed** — a fact to plant ("I like sushi with tuna").
- **question** — a later prompt that probes recall ("what should I order?").
- **expected** — what a correct answer must contain.

Kept constant across all runs so any change in score is attributable to the
parameter, not the questions (ADR-004). Editing the probe set creates a **new
baseline** — re-run prior configs if you need comparison, and say so loudly.

## How scoring works (the weakest link — keep it consistent)

Judging *"did it remember?"* is not self-evident, so the method is fixed and
explicit (ADR-006 in [DECISIONS.md](DECISIONS.md)):

- **Start simple:** keyword / substring match of the agent's answer against the
  probe's `expected`. Cheap, deterministic, transparent.
- **Upgrade only if needed:** move to an **LLM-as-judge** if simple matching is too
  brittle — but remember the judge has its own error, so you'd be measuring memory
  *through* it. Hold the judge constant across runs.
- **Non-negotiable:** the scoring method must be **identical across every run in a
  sweep**, or the comparison is meaningless.

## The no-memory baseline (control)

Every sweep includes a control run with **memory disabled** (ADR-007). A recall of
"70%" is meaningless until you know it's, say, "20%" without memory. Read every
memory result *against* this baseline — the baseline is the floor each config must
beat. Record it in [RESULTS.md](RESULTS.md) alongside the sweep.

## Handling nondeterminism

LLMs return different answers to identical inputs, so one run per config partly
measures randomness (ADR-008). Mitigate by:

- Setting **temperature = 0** where the model supports it, and/or
- Running each config **N times and averaging** (record N in
  [RESULTS.md](RESULTS.md)).

Don't report a single lucky number as truth.

## One parameter first; interactions later

Single-parameter sweeps come first for clean attribution (ADR-003). The interesting
behavior often lives in *interactions* (e.g. top-k × relevance-threshold) — treat a
2-parameter grid as a deliberate, clearly-labeled later step, not the default.

## What is sweepable

Only the knobs with actual dials are swept. See the [taxonomy scope table in
IDEA.md](IDEA.md#memory-taxonomy--the-words-this-lab-uses) for the full picture; in
short: the long-term / retrieval (RAG) layer is fully swept (strategy, top-k,
relevance threshold, namespace), short-term gets one knob (conversation window),
and session memory / context window / embeddings are context, not dials.

## Running a sweep

```bash
# one parameter, several values, against the fixed probe set
python -m harness.run --sweep top_k --values 1,3,5,10
```

The harness loops over the values, feeding the **same agent** a different config
each time (see [one app, many configs](DESIGN.md#one-app-many-configs--never-rebuilt-per-test)),
runs the probe set, scores each answer, and emits a side-by-side table.

## Recording results

Every sweep produces a table appended to [RESULTS.md](RESULTS.md), with the
held-constant settings, the probe-set version, the baseline, N (repeats), and a
short interpretation of *why* recall / relevance / latency moved. Use the sweep
template there.
