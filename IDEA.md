# IDEA.md

> Pipeline: **IDEA.md** (start here) → [DESIGN.md](DESIGN.md) →
> [DEVELOPMENT.md](DEVELOPMENT.md) → [TESTING.md](TESTING.md) →
> [DEPLOYMENT.md](DEPLOYMENT.md) ▶. This is the **why** of the project — the human
> idea a design grows from. For status & plan, see
> [DEVELOPMENT.md](DEVELOPMENT.md#iterations--status--plan); for how to work in the
> repo, see [AGENTS.md](AGENTS.md). Full map:
> [documentation map](AGENTS.md#documentation-map).

## Project: Agent Memory Lab

A small, focused project for building a Strands agent on Amazon Bedrock AgentCore
Runtime and **measuring how its memory behaves as you change parameters**. The goal
is learning, not production: a controlled harness where you can sweep one memory
setting at a time and see what happens to recall, relevance, and latency.

## The core question

> When I change a memory parameter, how does the agent's ability to remember
> change?

Most tutorials show you *how* to attach memory to an agent. They rarely show you
*how memory behaves* when you tune it. This project closes that gap with a
repeatable experiment.

## Memory taxonomy — the words this lab uses

"Memory" is overloaded. Before tuning anything, here is precisely what each term
means and **which kinds this lab actually tests**. If you remember one thing: an
agent's "memory" is several different mechanisms stacked together, and they fail
in different ways.

| Term | Plain meaning | Tested in this lab? | How / which knob |
|------|---------------|---------------------|------------------|
| **Long-term memory** | What the agent remembers **across sessions** — facts/preferences extracted from past conversations and recalled later. Survives beyond any single chat. | ✅ **Swept (core)** | AgentCore **strategies**: semantic / summarization / user-preference. The main event. |
| **Retrieval / RAG** | Retrieval-Augmented Generation: instead of stuffing everything into the context window, you **store** information and **fetch only the relevant bits** at query time, then add them to the prompt. | ✅ **Swept (core)** | **top-k**, **relevance threshold**, **namespace** — these *are* the retrieval knobs. See note below. |
| **Short-term memory** | What the agent remembers **within one conversation/session** — the recent turns kept verbatim in the context window. Gone when the session ends (unless persisted). | 🟡 **Swept (one knob)** | The **conversation window** (how many recent turns are kept verbatim). Limited but real. |
| **Session memory** | Persistence of a conversation so it survives a restart — the same session can be reloaded. Still scoped to *that* conversation. | 🔵 **Used, not swept** | Provided by AgentCore short-term persistence. It's on/off, not a dial — no value to sweep. |
| **Context window** | The fixed amount of text the model can "see" in a single call (the prompt + history you pass in). Hard limit, set by the model. Everything else exists to work *around* this limit. | ⚪ **Constraint (fixed)** | A model limit you can't "turn up." It's *why* the other knobs matter, not a variable. |
| **Embedding** | Turning text into a vector of numbers so "similar meaning" becomes "close in space" — what makes relevance-based retrieval possible. | 🟣 **Stretch only** | Swapping the embedding model is a [stretch idea](#stretch-ideas-later-not-now), not a core sweep. |

**Scope in one line:** the lab fully sweeps the **long-term / retrieval (RAG)
layer** (4 knobs — the richest part), sweeps **short-term** with one knob, and
treats **session memory, context window, and embeddings** as context you *use or
work around* rather than tune. So "memory taxonomy" here means *understand all six,
sweep the four that have dials.*

**How they fit together (the mental model):**

```
   ┌─────────────────────── one model call ───────────────────────┐
   │  CONTEXT WINDOW (hard size limit)                              │
   │   ├─ recent turns kept verbatim  ← SHORT-TERM / SESSION memory │
   │   └─ relevant facts fetched in   ← LONG-TERM memory, via       │
   │                                     RETRIEVAL/RAG (top-k,       │
   │                                     threshold, namespace,       │
   │                                     embeddings)                 │
   └───────────────────────────────────────────────────────────────┘
```

The agent can't remember everything (context window is finite), so it keeps a few
recent turns **directly** (short-term) and **fetches** older relevant facts on
demand (long-term via retrieval/RAG). This lab measures what happens to recall,
relevance, and latency as you tune each of those mechanisms.

> **On "is this RAG?"** Yes — AgentCore Memory *is* a managed retrieval-augmented
> system: it stores extracted memories and retrieves the relevant ones per query.
> The difference from classic document-RAG is *what* gets stored (facts/summaries
> extracted from conversations, not your own document corpus) and that AWS manages
> the store and retrieval for you. The tuning intuition transfers directly to any
> RAG system you build by hand.

## Goals

1. **Build** a minimal Python Strands agent that runs locally and deploys to
   AgentCore Runtime with no code changes.
2. **Attach** AgentCore Memory using its built-in strategies (semantic,
   summarization, user-preference).
3. **Test** memory empirically by sweeping parameters one at a time against a
   fixed set of probe questions, then scoring the results.
4. **Learn** which parameters matter most and build intuition that transfers to
   any agent framework.

## Non-goals

- Not a production system. No auth hardening, no multi-tenant concerns, no SLA.
- Not a benchmark suite. The probe set is small and hand-written, meant to teach,
  not to publish numbers.
- Not multi-agent orchestration. One agent, one memory store, kept deliberately
  simple.

## Parameters under test

The experiment varies these, holding everything else constant each run. The
**Layer** column ties each knob back to the [memory
taxonomy](#memory-taxonomy--the-words-this-lab-uses) above.

| Parameter | Layer | What it controls | Why it matters |
|-----------|-------|------------------|----------------|
| Memory strategy | Long-term | semantic / summarization / user-preference / combined | Biggest lever; changes what gets stored at all |
| Retrieval top-k | Retrieval/RAG | How many memories pulled per query | Too few misses facts; too many adds noise |
| Relevance threshold | Retrieval/RAG | Cutoff for "relevant enough" to retrieve | Trades recall against precision |
| Namespace scope | Retrieval/RAG | strategy / actor / session granularity | Controls what the agent can even see |
| Batch size | Long-term (write path) | Messages buffered before a write | Throughput vs. risk of losing buffered data |
| Conversation window | Short-term | Turns kept verbatim before summarizing | Short-term recall vs. context cost |

## How we measure

For each configuration:

- **Recall accuracy** — did the agent correctly remember the probed fact?
- **Relevance** — were retrieved memories on-topic for the question?
- **Latency** — wall-clock time per turn.

A run = (one config) x (the fixed probe set). Sweep one parameter, hold the rest,
record the scores, compare.

## Experiment design — making the numbers trustworthy

This is a *lab*, so the experiment must be sound, not just runnable. Four design
choices keep the tables honest:

1. **How scoring works (the weakest link — decide it explicitly).** "Did it
   remember?" is not self-evident. Each probe ships with an `expected` answer; we
   score recall by checking the agent's answer against it. Start simple
   (keyword/substring match on the expected fact); upgrade to an **LLM-as-judge**
   only if simple matching is too brittle — and remember the judge has its own
   error, so you're measuring memory *through* it. Whatever method, it must be the
   **same across all runs** in a sweep, or the comparison is meaningless. (Logged
   as an ADR in [DECISIONS.md](DECISIONS.md).)

2. **A no-memory baseline (the control).** Always run the probe set once with
   **memory turned off**. A recall of "70%" means nothing until you know it's,
   say, "20%" without memory. Every sweep is read *against* this control.

3. **Handle nondeterminism.** LLMs give different answers to the same input. One
   run per config partly measures noise. Mitigate by setting **temperature = 0**
   where possible and/or running each config **N times and averaging** (note N in
   [RESULTS.md](RESULTS.md)). Don't report a single lucky number as truth.

4. **One parameter first; interactions later.** Single-parameter sweeps come first
   for clean attribution (see ADR-003). But the interesting behavior often lives in
   *interactions* (e.g. top-k × relevance-threshold). Treat a 2-parameter grid as a
   deliberate, later step — not the default — and label it clearly when you do it.

## Why Python

The full AgentCore Memory system — strategies, the session manager, retrieval
config — is available and complete in Python today. The TypeScript SDK can deploy
to AgentCore Runtime but its managed Memory module is still in progress, so Python
is the path that lets us actually sweep the parameters we care about.

## Success criteria

You can run a single command, sweep a memory parameter across several values, and
read a table that shows how recall, relevance, and latency moved. From that table
you can explain *why* the agent remembered (or forgot) something.

## Stretch ideas (later, not now)

- Swap embedding models and re-run the sweep.
- Add recency/decay weighting and measure its effect on old vs. new facts.
- Port the agent loop to the TypeScript SDK once its Memory module ships, and
  compare a self-built memory layer against the managed one.
