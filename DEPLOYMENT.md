# DEPLOYMENT.md

How to deploy **Agent Memory Lab** and the AWS infrastructure it runs on — from
local runs to Amazon Bedrock AgentCore Runtime, including account/IAM setup, the
memory resource, environment values, and **cost & teardown**. (This doc absorbed
the former `INFRASTRUCTURE.md`.) The headline: the **same agent code** runs both
places; deployment requires no code changes.

> ◀ Pipeline: [IDEA.md](IDEA.md) → [DESIGN.md](DESIGN.md) →
> [DEVELOPMENT.md](DEVELOPMENT.md) → [TESTING.md](TESTING.md) → **DEPLOYMENT.md**
> (last stage). Local setup & commands are in [DEVELOPMENT.md](DEVELOPMENT.md).
> Full map: [documentation map](AGENTS.md#documentation-map). Deployment is built in
> Iteration 6; the memory resource in Iteration 2 — see the
> [iteration plan](DEVELOPMENT.md#iteration-plan).

---

## Part 1 — Infrastructure (AWS prerequisites)

Read this before Iteration 2 (creating the memory resource) or any run that touches
Bedrock.

### Prerequisites

- An **AWS account** with access to:
  - **Amazon Bedrock** (and the specific model in `BEDROCK_MODEL_ID` enabled in
    your region — Bedrock model access is opt-in per model).
  - **Bedrock AgentCore** (Memory + Runtime).
- **AWS credentials** configured locally (e.g. via `aws configure` or environment
  credentials) for the same account/region.
- An **IAM role/permissions** allowing the agent and CLI to call Bedrock, AgentCore
  Memory, AgentCore Runtime, CloudWatch Logs, and (for deploy) ECR. The `agentcore`
  CLI can help provision the execution role; verify exact required permissions
  against current AWS docs.

### Provisioning with Terraform (`infra/`)

Infrastructure is defined as code in [`infra/`](infra/) (Terraform). **Iteration 1
scope is Bedrock access only**: an IAM role + a narrowly-scoped policy granting
`bedrock:InvokeModel` on the configured model. Memory, ECR, and Runtime resources
are added in their own iterations.

**Remote state (S3).** State lives in an S3 bucket — versioned, encrypted, with
S3-native locking (ADR-012). The bucket is created once by a separate bootstrap
config (it can't store its own state in the bucket it creates). In a **fresh
clone**, run the bootstrap first:

```bash
# 1) one-time: create the state bucket (uses LOCAL state)
cd infra/bootstrap
terraform init && terraform apply
terraform output state_bucket_name      # matches the bucket in ../backend.tf

# 2) the main config (uses the S3 backend from backend.tf)
cd ..
cp terraform.tfvars.example terraform.tfvars   # set region + model id
terraform init                                 # configures the S3 backend
terraform plan
terraform apply
terraform output                               # account, region, agent_role_arn
```

> The bucket name is deterministic
> (`agent-memory-lab-tfstate-<account-id>-<region>`) and hardcoded in
> [`infra/backend.tf`](infra/backend.tf). If your account/region differ, update
> that block to match the bootstrap output.

State files are git-ignored; only the `.tf` config and `.terraform.lock.hcl` are
committed. To verify Bedrock access independently of Terraform, run the AWS CLI
check: [`scripts/verify_bedrock.sh`](scripts/verify_bedrock.sh).

> **Verify against current docs.** AgentCore is evolving; confirm required IAM
> actions, per-region service availability, the role's trust principal, and CLI
> commands against current AWS documentation before relying on specifics here.

### The memory resource

The agent depends on a **managed AgentCore Memory resource**, created **once** and
then referenced by ID. As of Iteration 2 it's defined in Terraform
([`infra/memory.tf`](infra/memory.tf)):

- **Resources:** `aws_bedrockagentcore_memory` (the store) +
  `aws_bedrockagentcore_memory_strategy` (a `SEMANTIC` long-term strategy). Created
  by the same `terraform apply` as the rest of `infra/`. **Provisioning takes
  ~2–3 minutes.**
- **`event_expiry_duration`** is in **days** (provider range 7–365; default 90).
- **`MEMORY_ID`** comes from `terraform output memory_id`; set it in `.env`. It's
  consumed by the agent (local *and* deployed).
- **Namespace scheme — `semantic/{actorId}`** (the `memory_namespace` variable).
  `{actorId}` is filled by AgentCore at runtime, so each actor's facts are recalled
  across their sessions. ⚠️ **This namespace must match what the agent references at
  retrieval time (Iteration 3), or recall silently returns nothing** (see gotchas in
  [DEVELOPMENT.md](DEVELOPMENT.md#critical-gotchas)).
- **Verify independently:**
  `aws bedrock-agentcore-control get-memory --memory-id "$MEMORY_ID"` should show
  `status: ACTIVE` and the semantic strategy.

### Environment / config values

Externalize so nothing is hardcoded (ADR-002). A `.env` (git-ignored) or your shell
environment should provide:

| Variable | Meaning | Source |
|----------|---------|--------|
| `AWS_REGION` | Region for Bedrock + AgentCore | your choice (must have the services) |
| `BEDROCK_MODEL_ID` | The Bedrock model the agent uses | enabled Bedrock model |
| `MEMORY_ID` | The created AgentCore Memory resource | output of Iteration 2 setup |
| `ACTOR_ID` | Who the memories belong to | generated per run (often timestamped) |
| `SESSION_ID` | The conversation/session scope | generated per run (often timestamped) |

> **Never commit credentials or a real `.env`.** Keep secrets out of git.

---

## Part 2 — Deploying

### Local vs. AgentCore Runtime

| Concern | Local | AgentCore Runtime |
|---------|-------|-------------------|
| Entry point | HTTP server / direct calls | `/ping` + `/invocations` |
| Packaging | venv | Docker image in ECR |
| Memory | same memory resource by ID | same memory resource by ID |
| Isolation | single process | per-session microVM |
| Observability | console logs | CloudWatch + OpenTelemetry |

The agent exposes the AgentCore HTTP contract (`/ping` health check, `/invocations`
for prompts) so the *same* code serves locally and in the Runtime.

### Deploy commands

```bash
# Deploy to AgentCore Runtime
agentcore deploy

# Tail runtime logs
aws logs tail /aws/bedrock-agentcore/runtimes/<name> --region $AWS_REGION --since 1h
```

Deploy with the `agentcore` CLI. The Runtime provides session isolation, persistent
memory, and observability without app changes. The same CLI flow works for Python
and TypeScript agents.

### What carries over from local

- **The memory resource** — referenced by `MEMORY_ID`; the Runtime points at the
  same resource you used locally.
- **Environment values** — `AWS_REGION`, `BEDROCK_MODEL_ID`, `MEMORY_ID`, etc. must
  be present in the Runtime environment too.

### Deployment gotchas

- **Cold-start latency.** The first invocation after deploy is a cold start; warm up
  before recording any latency numbers, or your timing is skewed. (Also in the
  [testing method](TESTING.md#handling-nondeterminism) and
  [DEVELOPMENT.md gotchas](DEVELOPMENT.md#critical-gotchas-read-before-touching-memory-code).)
- **Same memory ID, both environments.** A mismatched `MEMORY_ID` between local and
  Runtime means you're testing against a different store — recall scores won't line
  up. Keep it identical.
- **Verify the CLI/SDK flow against current docs.** The `agentcore` deploy flow
  evolves; confirm command names and required IAM permissions against current AWS
  docs before relying on them.

---

## Part 3 — Cost & teardown

**This project costs real money to run.** It is a learning lab, but the AWS
resources are billable:

- **Bedrock model calls** — every probe turn is an inference call. A sweep =
  (values) × (probes) × (repeats) calls, plus the no-memory baseline. Costs scale
  with how big your sweeps are.
- **AgentCore Memory** — storage and retrieval of memories.
- **AgentCore Runtime** (once deployed) — compute while the runtime exists, plus
  ECR image storage and CloudWatch logs.

**Keep cost down:**

- Keep the probe set small (it already is, by design — ADR-004).
- Use modest sweep value lists; you don't need 20 values to see a trend.
- Be deliberate about repeat count `N` for nondeterminism (more repeats = more
  calls).

**Tear down when done:**

- Delete deployed AgentCore Runtimes you're no longer using.
- Delete the memory resource if you don't need its stored memories (recreating it is
  cheap; leaving it costs storage).
- Remove ECR images and old CloudWatch log groups if cleaning up fully.

> Confirm current Bedrock / AgentCore pricing in the AWS console or pricing pages
> before running large sweeps — model and service pricing changes over time.
