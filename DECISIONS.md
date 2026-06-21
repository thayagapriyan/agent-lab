# DECISIONS.md

**The durable record of *why*.** Lightweight architecture decision records (ADRs):
each one captures a choice, the context that forced it, and what it commits us to.
This is the project's reasoning, kept separate from history so it survives even
when the design changes.

> Difference from the other docs: [CHANGELOG.md](CHANGELOG.md) records *what
> happened, when*; [DESIGN.md](DESIGN.md) records *what the design is now*; this
> file records *why the design is that way*. Part of the tracking group:
> [RESULTS.md](RESULTS.md) ↔ **DECISIONS.md** (the status board lives in
> [DEVELOPMENT.md](DEVELOPMENT.md#iterations--status--plan)). For the doc map, see
> the [documentation map](AGENTS.md#documentation-map).

## How to add a decision

- Append a new ADR at the **bottom**, numbered sequentially (`ADR-00N`).
- Keep it short: context → decision → consequences. A few sentences each.
- Don't delete superseded ADRs. Mark them `Superseded by ADR-00M` and leave them.
- A decision belongs here when reversing it later would be costly or confusing —
  not for routine choices.

### ADR template

```markdown
## ADR-00N: <short title>
- **Status:** Accepted | Superseded by ADR-00M | Deprecated
- **Date:** YYYY-MM-DD
- **Context:** <the forces / constraints that made a choice necessary>
- **Decision:** <what we chose>
- **Consequences:** <what this commits us to; trade-offs accepted>
```

---

## ADR-001: Python, not TypeScript
- **Status:** Accepted
- **Date:** 2026-06-21
- **Context:** The project's purpose is to sweep AgentCore Memory parameters. The
  full Memory system (strategies, session manager, retrieval config) is complete
  in the Python SDK; the TypeScript Memory module is still in progress.
- **Decision:** Build in Python (3.10+).
- **Consequences:** We can sweep every parameter we care about today. A future TS
  port (see [IDEA.md stretch ideas](IDEA.md#stretch-ideas-later-not-now)) would
  require hand-building the memory layer until the managed module ships.

## ADR-002: Inject the memory config; never hardcode it
- **Status:** Accepted
- **Date:** 2026-06-21
- **Context:** The experiment requires varying one memory parameter at a time. If
  memory settings were baked into agent logic, every run would need a code edit.
- **Decision:** All tunable memory settings flow through a single config object
  passed to the session manager. The agent reads its memory behavior entirely from
  this object.
- **Consequences:** The harness sweeps by constructing variant configs — no agent
  changes per run. This is *the* design seam; protect it. (See
  [DESIGN.md](DESIGN.md#the-configuration-seam).)

## ADR-003: One parameter per sweep run
- **Status:** Accepted
- **Date:** 2026-06-21
- **Context:** Changing two parameters at once confounds results — you can't
  attribute a score change to a cause.
- **Decision:** Each run varies exactly one memory parameter; all others held
  constant.
- **Consequences:** Clean attribution and interpretable tables, at the cost of
  more runs to explore the space. Recorded results in
  [RESULTS.md](RESULTS.md) are only comparable within a single-parameter sweep.

## ADR-004: Fixed, small, hand-written probe set
- **Status:** Accepted
- **Date:** 2026-06-21
- **Context:** This is a teaching instrument, not a benchmark. The probe set must
  not change between runs, or prior scores stop being comparable.
- **Decision:** A small, fixed set of `(seed, question, expected)` triples, held
  constant across all runs. Editing it creates a new baseline (re-run prior
  configs).
- **Consequences:** Fast iteration and clean attribution; the numbers teach rather
  than publish. Not suitable as a published benchmark — by design.

## ADR-006: Scoring method — start with exact/keyword match, LLM-judge only if needed
- **Status:** Accepted
- **Date:** 2026-06-21
- **Context:** The whole project hinges on judging *"did the agent remember the
  fact?"* — which is not self-evident. A subjective or inconsistent scorer makes
  every table untrustworthy.
- **Decision:** Each probe carries an `expected` answer. Score recall by matching
  the agent's answer against it, starting with simple keyword/substring matching.
  Move to **LLM-as-judge** only if simple matching proves too brittle. The scoring
  method must be identical across all runs within a sweep.
- **Consequences:** Cheap, deterministic, and transparent to start. If we adopt an
  LLM judge later, we accept that the judge adds its own measurement error and must
  hold it constant. (See [IDEA.md experiment design](IDEA.md#experiment-design--making-the-numbers-trustworthy).)

## ADR-007: Always run a no-memory baseline as the control
- **Status:** Accepted
- **Date:** 2026-06-21
- **Context:** A recall score has no meaning without a reference point. "70%
  recall" is only interpretable against what the agent scores with no memory at
  all.
- **Decision:** Every sweep includes a control run with **memory disabled**. All
  memory results are reported relative to this baseline in
  [RESULTS.md](RESULTS.md).
- **Consequences:** One extra run per sweep, in exchange for results that actually
  mean something. The baseline is the floor every config must beat.

## ADR-008: Mitigate LLM nondeterminism (temperature 0 and/or repeated runs)
- **Status:** Accepted
- **Date:** 2026-06-21
- **Context:** LLMs return different answers to identical inputs. A single run per
  config partly measures randomness, not the parameter under test.
- **Decision:** Reduce nondeterminism by setting **temperature = 0** where
  supported, and/or running each config **N times and averaging**. Record N
  alongside each table in [RESULTS.md](RESULTS.md).
- **Consequences:** More runs / more cost for more stable numbers. Single-run
  results are treated as indicative, not definitive. Single-parameter sweeps stay
  the default (ADR-003); multi-parameter grids are a deliberate later step.

## ADR-005: Separate mutable status from immutable history
- **Status:** Accepted (updated — see ADR-011)
- **Date:** 2026-06-21
- **Context:** A single combined doc mixes a mutable plan with an immutable log and
  grows unwieldy; agents need one clear "where are we" entry point.
- **Decision:** The mutable status board + iteration plan is kept separate from the
  append-only history ([CHANGELOG.md](CHANGELOG.md)). Reasoning lives in this file;
  results in [RESULTS.md](RESULTS.md). *(The status board originally lived in a
  standalone `ITERATION.md`; ADR-011 later folded it into
  [DEVELOPMENT.md](DEVELOPMENT.md#iterations--status--plan).)*
- **Consequences:** The status board stays focused, history stays honest, and each
  doc has one job. Cost: agents must keep several files in sync (enforced by the
  [agent working loop](AGENTS.md#agent-working-loop)).

## ADR-011: Iterations live in DEVELOPMENT.md; doc map lives in AGENTS.md
- **Status:** Accepted (supersedes the ITERATION.md placement in ADR-005)
- **Date:** 2026-06-21
- **Context:** A standalone `ITERATION.md` split "how to build" from "what's the
  status of the build," and agents kept treating it as a separate source of truth.
  The user wanted one read-first doc that owns the iterations.
- **Decision:** Fold the status board + iteration plan into
  [DEVELOPMENT.md](DEVELOPMENT.md#iterations--status--plan) (now the read-first doc),
  and move the documentation map into [AGENTS.md](AGENTS.md#documentation-map) (the
  contract that references all docs). Delete `ITERATION.md`. The tracking group
  becomes [RESULTS.md](RESULTS.md) ↔ [DECISIONS.md](DECISIONS.md).
- **Consequences:** One fewer file; build + status read together. DEVELOPMENT.md is
  longer (mitigated with jump-links and clear sections). All former
  `ITERATION.md#...` links now point at DEVELOPMENT.md or AGENTS.md.

## ADR-009: Provision AWS infrastructure with Terraform
- **Status:** Accepted
- **Date:** 2026-06-21
- **Context:** The project needs AWS resources (IAM for Bedrock now; AgentCore
  Memory, ECR, Runtime later). Ad-hoc console clicks or one-off scripts are not
  reproducible or reviewable, and make teardown error-prone.
- **Decision:** Define infrastructure as code in `infra/` using **Terraform**.
  Iteration 1 scope is **Bedrock access only** (IAM role + scoped
  `bedrock:InvokeModel` policy); later resources are added per iteration. State is
  local for this learning lab.
- **Consequences:** Reproducible, reviewable, tear-down-able infra. Adds Terraform
  as a tool dependency. Local state is fine solo; move to a remote backend if ever
  shared. Verify AgentCore IAM principals/actions against current AWS docs.

## ADR-010: Smoke test is mock-by-default, real Bedrock is opt-in
- **Status:** Accepted
- **Date:** 2026-06-21
- **Context:** A "prompt → response" smoke test that always calls Bedrock needs AWS
  credentials and costs money on every run, so it can't run offline or in plain CI.
  But a purely mocked test never proves the real Bedrock wiring.
- **Decision:** The smoke test uses an **injected mock model by default** (free,
  offline, proves agent wiring + the config seam). Setting **`RUN_LIVE=1`** runs an
  additional test that calls real Bedrock. A separate AWS CLI script
  (`scripts/verify_bedrock.sh`) checks model access without invoking the model.
- **Consequences:** Fast, free, always-green default; real verification on demand.
  Requires a model-factory seam in the agent (`build_model`) — which also matches
  the project's "inject, don't hardcode" philosophy (ADR-002).
