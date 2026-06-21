# ARCHITECTURE.md

Technical design for **Agent Memory Lab** — a Python Strands agent on AgentCore
Runtime with a memory parameter-sweep harness.

## High-level shape

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

The same agent code runs two ways: **locally** (an Express-style HTTP server, or
direct function calls in tests) and **on AgentCore Runtime** (containerized,
behind `/ping` and `/invocations`). Deployment requires no code changes.

## Components

### 1. Agent Service

The Strands agent itself. Responsibilities:

- Define the model (Bedrock, e.g. a Claude model via Bedrock).
- Register any tools the probes need (kept minimal for this project).
- Attach memory via an `AgentCoreMemorySessionManager` built from a config object.
- Expose the AgentCore HTTP contract: a `/ping` health check and an
  `/invocations` endpoint that accepts a prompt and streams back a response.

The memory configuration is **injected**, not hardcoded — that is the seam the
harness uses to sweep parameters.

### 2. Memory Layer (AgentCore Memory)

A managed memory resource, created once (via the AgentCore CLI or a setup script),
then referenced by ID from the agent. It supports:

- **Short-term memory** — conversation persistence within a session.
- **Long-term memory** via strategies:
  - *semantic* — extracts and stores factual information from conversations.
  - *summarization* — compresses sessions into summaries for cheaper retrieval.
  - *user-preference* — learns and stores preferences across sessions.

Memories are organized by **namespace**, a slash-delimited hierarchy that scopes
data by strategy, actor, and session. The `{actorId}` and `{sessionId}`
placeholders are filled at runtime. Retrieval is governed by a retrieval config
(top-k, relevance threshold) that the harness varies.

### 3. Experiment Harness

The part that makes this a *lab*. Responsibilities:

- Hold the list of configurations to test (one parameter swept, rest fixed).
- For each config: instantiate/point the agent at that memory config, run the
  full probe set, collect answers.
- Score each answer (recall, relevance) and record latency.
- Emit a comparison table / CSV so configs sit side by side.

### 4. Probe Set

A fixed, hand-written set of (seed, question, expected) triples. Seeds plant facts
("I like sushi with tuna"); questions probe recall later ("what should I order?");
expected values define what counts as correct. Kept constant across all runs so
that any change in score is attributable to the parameter, not the questions.

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

## Deployment

| Concern | Local | AgentCore Runtime |
|---------|-------|-------------------|
| Entry point | HTTP server / direct calls | `/ping` + `/invocations` |
| Packaging | venv | Docker image in ECR |
| Memory | same memory resource by ID | same memory resource by ID |
| Isolation | single process | per-session microVM |
| Observability | console logs | CloudWatch + OpenTelemetry |

Deploy with the `agentcore` CLI. Runtime provides session isolation, persistent
memory, and observability without app changes.

## Environment / config values

Externalize so nothing is hardcoded:

- `AWS_REGION`
- `BEDROCK_MODEL_ID`
- `MEMORY_ID` (from the created memory resource)
- `ACTOR_ID` / `SESSION_ID` (generated per run, often timestamped)

## Key design decisions

- **Inject memory config, never hardcode it.** This is what makes sweeping
  possible. If memory settings were baked into the agent, every run would need a
  code edit.
- **Keep the probe set fixed and small.** A teaching instrument, not a benchmark.
  Small means fast iteration; fixed means clean attribution.
- **One agent, one session per run.** The session manager currently supports one
  agent per session; respecting that keeps results clean and avoids warnings.
- **Flush buffered memory.** When `batch_size > 1`, messages are buffered and only
  written when the buffer fills — so always close the session (context manager or
  `close()` in a `finally`) or buffered memories are lost and recall scores lie.

## Risks & gotchas

- **Lost writes from batching.** The single most likely source of confusing
  results. Always flush.
- **Namespace mismatch.** The namespace you set at strategy-creation time must be
  the one you reference at retrieval; a mismatch silently returns nothing.
- **Confounded sweeps.** Change one parameter per run. Changing two makes the
  table meaningless.
- **Cold-start latency.** First invocation after deploy skews timing; warm up
  before recording latency.
