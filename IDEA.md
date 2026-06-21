# IDEA.md

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

The experiment varies these, holding everything else constant each run:

| Parameter | What it controls | Why it matters |
|-----------|------------------|----------------|
| Memory strategy | semantic / summarization / user-preference / combined | Biggest lever; changes what gets stored at all |
| Retrieval top-k | How many memories pulled per query | Too few misses facts; too many adds noise |
| Relevance threshold | Cutoff for "relevant enough" to retrieve | Trades recall against precision |
| Namespace scope | strategy / actor / session granularity | Controls what the agent can even see |
| Batch size | Messages buffered before a write | Throughput vs. risk of losing buffered data |
| Conversation window | Turns kept verbatim before summarizing | Short-term recall vs. context cost |

## How we measure

For each configuration:

- **Recall accuracy** — did the agent correctly remember the probed fact?
- **Relevance** — were retrieved memories on-topic for the question?
- **Latency** — wall-clock time per turn.

A run = (one config) x (the fixed probe set). Sweep one parameter, hold the rest,
record the scores, compare.

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
