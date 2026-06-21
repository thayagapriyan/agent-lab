# DESIGN.md

The design of **Agent Memory Lab** — the big picture, the components, how data
flows through them, and the one seam that makes the whole experiment possible.
This is the single design doc (it absorbed the former `ARCHITECTURE.md`).

> ◀ Pipeline: [IDEA.md](IDEA.md) → **DESIGN.md** → [DEVELOPMENT.md](DEVELOPMENT.md)
> → [TESTING.md](TESTING.md) → [DEPLOYMENT.md](DEPLOYMENT.md). The *why* behind the
> design is in [DECISIONS.md](DECISIONS.md); the build plan is in
> [ITERATION.md](ITERATION.md). Full map:
> [documentation map](ITERATION.md#documentation-map). Change the design? Update the
> relevant iteration in [ITERATION.md](ITERATION.md) and log it in
> [CHANGELOG.md](CHANGELOG.md).

## The big picture

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

**Four parts:** a fixed **probe set** of questions, **one agent** (Strands), a
managed **AgentCore Memory** layer, and an **experiment harness** that sweeps one
memory parameter at a time and scores the result. The core idea: build the agent
once, then vary only an injected **config object** to test different memory
settings — never edit or copy the agent per test (see
[one app, many configs](#one-app-many-configs--never-rebuilt-per-test)).

The same agent code runs two ways: **locally** (an HTTP server, or direct function
calls in tests) and **on AgentCore Runtime** (containerized, behind `/ping` and
`/invocations`). Deployment requires no code changes — see
[DEPLOYMENT.md](DEPLOYMENT.md).

## Components

### 1. Agent Service

The Strands agent itself. Responsibilities:

- Define the model (Bedrock, e.g. a Claude model via Bedrock).
- Register any tools the probes need (kept minimal for this project).
- Attach memory via an `AgentCoreMemorySessionManager` built from a config object.
- Expose the AgentCore HTTP contract: a `/ping` health check and an
  `/invocations` endpoint that accepts a prompt and streams back a response.

The memory configuration is **injected**, not hardcoded — that is the seam the
harness uses to sweep parameters (see [the configuration seam](#the-configuration-seam)).

### 2. Memory Layer (AgentCore Memory)

A managed memory resource, created once (see
[DEPLOYMENT.md](DEPLOYMENT.md#the-memory-resource)), then referenced by ID from the
agent. It
supports:

- **Short-term memory** — conversation persistence within a session.
- **Long-term memory** via strategies:
  - *semantic* — extracts and stores factual information from conversations.
  - *summarization* — compresses sessions into summaries for cheaper retrieval.
  - *user-preference* — learns and stores preferences across sessions.

Memories are organized by **namespace**, a slash-delimited hierarchy that scopes
data by strategy, actor, and session. The `{actorId}` and `{sessionId}`
placeholders are filled at runtime. Retrieval is governed by a retrieval config
(top-k, relevance threshold) that the harness varies. For how these map to memory
concepts, see the [taxonomy in IDEA.md](IDEA.md#memory-taxonomy--the-words-this-lab-uses).

### 3. Experiment Harness

The part that makes this a *lab*. Responsibilities:

- Hold the list of configurations to test (one parameter swept, rest fixed).
- For each config: point the **same** agent at that memory config, run the full
  probe set, collect answers.
- Score each answer (recall, relevance) and record latency — see
  [TESTING.md](TESTING.md) for the method.
- Emit a comparison table / CSV to [RESULTS.md](RESULTS.md) so configs sit side by
  side.

### 4. Probe Set

A fixed, hand-written set of `(seed, question, expected)` triples. Seeds plant
facts ("I like sushi with tuna"); questions probe recall later ("what should I
order?"); expected values define what counts as correct. Kept constant across all
runs so any change in score is attributable to the parameter, not the questions.
Details and scoring in [TESTING.md](TESTING.md).

## One app, many configs — never rebuilt per test

**This is the most important design rule in the project.** You build **one** agent
app. To test a different memory configuration you **do not touch the agent** — you
pass it a different **config object**. (See ADR-002 in [DECISIONS.md](DECISIONS.md).)

```
        ❌ WRONG — a copy of the agent per test case
   test top_k=1  →  agent_v1   ← editing/copying the agent per case
   test top_k=3  →  agent_v2      = confounded results, unmaintainable
   test top_k=5  →  agent_v3

        ✅ RIGHT — one agent, config injected
                    ┌─────────────────┐
   config(top_k=1) →│                 │
   config(top_k=3) →│   ONE agent     │→ run probes → score
   config(top_k=5) →│ (never changes) │
   config(top_k=10)→│                 │
                    └─────────────────┘
            the harness loops, swapping only the config
```

If you ever find yourself editing agent logic to change a memory setting, **stop**
— lift it into the config. That edit is the signal the design has been broken.

## Build once, run many

Building the harness and running every sweep are **different activities**:

- **Build the machinery once** (Iterations 1–5): the agent, the memory wiring, the
  probe set, the scorer, and the sweep runner. This is iteration work.
- **Run the cases operationally** (Iteration 7 onward): sweeping `top_k`, then
  `relevance_threshold`, then `strategy`, then `conversation_window` is just
  *running the same harness with different flags*. These are **runs, not new
  iterations** — each produces a table appended to [RESULTS.md](RESULTS.md).

So the iteration plan deliberately builds the capability to test every sweepable
knob but only *demonstrates* one sweep end-to-end (Iteration 5/7). The rest are
operational runs you do afterward — no new code, no new iterations.

## Data flow for one run

1. Harness picks a config (e.g. `top_k = 3`).
2. Harness builds a memory config + session manager for that setting.
3. For each probe: send seed turns, then the question turn, capture the answer.
4. Score answer vs. expected; record latency.
5. Aggregate per-config scores; move to next config.

## The configuration seam

Everything tunable lives in one config object passed to the session manager:

```python
# illustrative shape — confirm exact fields against current SDK docs
config = AgentCoreMemoryConfig(
    memory_id=MEM_ID,
    actor_id=ACTOR_ID,
    session_id=SESSION_ID,
    retrieval_config={
        "top_k": 3,            # swept
        "relevance_threshold": 0.5,  # swept
        # namespace selection here
    },
    # batch_size, etc.
)
```

Because the agent reads its memory behavior entirely from this object, the harness
sweeps parameters by constructing variant configs — no changes to agent logic.

> Treat field names above as a sketch. The AgentCore Memory SDK evolves; verify
> against the current docs before relying on exact parameter names.

## Key design decisions

These are summarized here and recorded in full as ADRs in
[DECISIONS.md](DECISIONS.md):

- **Inject memory config, never hardcode it** (ADR-002). What makes sweeping
  possible.
- **One parameter per sweep** (ADR-003). Clean attribution.
- **Keep the probe set fixed and small** (ADR-004). A teaching instrument, not a
  benchmark.
- **One agent, one session per run.** The session manager currently supports one
  agent per session; respecting that keeps results clean and avoids warnings.
- **Flush buffered memory.** When `batch_size > 1`, messages are buffered and only
  written when the buffer fills — always close the session or buffered memories are
  lost and recall scores lie. (See gotchas in [DEVELOPMENT.md](DEVELOPMENT.md).)
