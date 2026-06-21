# RESULTS.md

**The deliverable.** This is where sweep results live — the tables that show how
**recall, relevance, and latency** moved as one memory parameter was varied. Per
[IDEA.md](IDEA.md#success-criteria), success is: run a sweep, read a table here,
and explain *why* the agent remembered (or forgot).

> Empty until [Iteration 5](ITERATION.md#iteration-5--sweep-harness-) produces the
> first sweep. Each sweep gets its own section, appended below. For the reasoning
> behind the methodology, see [DECISIONS.md](DECISIONS.md); for what was done when,
> see [CHANGELOG.md](CHANGELOG.md). Doc map:
> [documentation map](ITERATION.md#documentation-map).

## How to record a sweep

- One section per sweep. **One parameter varies per sweep** (ADR-003) — note the
  held-constant settings so the result is reproducible.
- Fill the table, then write a short **interpretation**: *why* the numbers moved.
- Record the probe-set version. If the probe set changed, prior results are no
  longer comparable (ADR-004) — say so.
- Keep older sweeps; append new ones below.

### Sweep template

```markdown
## Sweep: <parameter> — <date>

**Probe set:** <version/hash, # of probes>
**Held constant:** strategy=…, top_k=…, threshold=…, namespace=…, batch_size=…,
window=…  (list everything except the swept parameter)
**Environment:** region=…, model=…, memory_id=…

| <param> | recall | relevance | latency (s) |
|---------|--------|-----------|-------------|
| …       | …      | …         | …           |

**Interpretation:**
- <why recall moved>
- <why relevance moved>
- <why latency moved>
- <takeaway / what to sweep next>
```

---

_No sweeps recorded yet. The first will land with Iteration 5._

<!--
Example shape (delete when the first real sweep is added):

## Sweep: top_k — 2026-07-01

**Probe set:** v1, 10 probes
**Held constant:** strategy=semantic, threshold=0.5, namespace=actor, batch_size=1, window=10
**Environment:** region=us-east-1, model=<id>, memory_id=<id>

| top_k | recall | relevance | latency (s) |
|-------|--------|-----------|-------------|
| 1     | 0.6    | 0.95      | 1.2         |
| 3     | 0.8    | 0.90      | 1.4         |
| 5     | 0.8    | 0.80      | 1.6         |
| 10    | 0.9    | 0.65      | 2.1         |

**Interpretation:**
- Recall rises with top_k (more memories pulled = more chances to hit the fact).
- Relevance falls as top_k grows (extra memories are off-topic noise).
- Latency grows with top_k (more retrieval + more context to process).
- Takeaway: top_k=3 is the knee — near-max recall before relevance degrades.
-->
