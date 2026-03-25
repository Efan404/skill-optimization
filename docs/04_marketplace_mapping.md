# Marketplace Mapping: From Benchmark Skills to Reusable Assets

## Important Framing Note

The marketplace mapping in this demo is a **conceptual projection** — it demonstrates how the skill schema and evidence format could integrate with marketplace platforms like EvoMap. It is NOT validated marketplace evidence.

**What this demo proves about marketplace readiness:**
- That skills can be structured in a machine-readable schema
- That skills can carry versioned evidence (dev/test results, changelogs)
- That the schema format is compatible with marketplace asset concepts

**What this demo does NOT prove:**
- Cross-model generalization (only tested on DeepSeek Chat)
- Large-sample statistical validity (demo-level sample size)
- Production reliability (single-turn QA, not agentic execution)

The connection to marketplace assets is **motivation and future direction**, not a validated conclusion.

## Context

EvoMap is an AI agent marketplace where capabilities are organized as composable, tradable assets:

- **Gene**: Atomic unit of capability — a single, focused procedure or strategy
- **Capsule**: Gene + validation evidence — a capability bundled with proof of effectiveness
- **Recipe**: Multi-gene workflow — a composition of capabilities that work together
- **GDI (Gene Discovery Index)**: Ranking system based on quality, usage, social signals, and freshness

## Mapping: Skill Optimization -> EvoMap Assets

### Asset Type Mapping

| EvoMap Concept | Skill Optimization Equivalent | Example |
|----------------|-------------------------------|---------|
| **Gene** | Atomic skill — single task-type procedure | "LP solver procedure" |
| **Capsule** | Skill + evidence bundle — skill with benchmark validation, error analysis, version history | "LP solver v2 + ORQA results" |
| **Recipe** | Multi-skill workflow — task router + domain-specific skills | "Classify OR problem type -> apply matched skill" |

### Why This Mapping Matters

Traditional prompt engineering produces **disposable artifacts** — prompts that work for one task but carry no evidence, no versioning, and no reuse potential.

The skill optimization approach produces **structured artifacts** because each skill carries:

1. **Structured format** — machine-readable schema, not free-form text
2. **Benchmark evidence** — tested on known tasks with dev/test separation
3. **Error analysis** — documented failure modes and fixes
4. **Version history** — traceable evolution from v0 to v2 with changelogs
5. **Reproducibility metadata** — model, temperature, exact prompts used
6. **Scaffold control** — evidence that value comes from domain content, not just structure

This transforms skills from prompt hacks into artifacts that are **potentially publishable, rankable, and improvable** — though Phase 1 evidence is demo-level only.

## Demo Marketplace Card Format

Each validated skill produces a **demo metadata card** (not production marketplace evidence):

```yaml
# NOTE: This is demo metadata showing the schema format.
# Evidence strength is demo-level and requires cross-model,
# larger-sample validation before marketplace publication.

asset_name: "or-linear-programming"
asset_type: "capsule"
domain: "operations_research"
supported_models: ["deepseek-chat"]  # Only validated on this single model
evidence:
  evidence_level: "demo"             # NOT "validated" or "production"
  benchmark: "ORQA"
  methodology:
    dev_test_split: true
    scaffold_controlled: true
    optimizer_blind_to_test: true
  dev_set:
    n_tasks: 5
    conditions:
      baseline: { accuracy: 0.40 }
      generic_scaffold: { accuracy: 0.40 }
      v0_self_generated: { accuracy: 0.40 }
      v1_curated: { accuracy: 0.60 }
      v2_optimized: { accuracy: 0.80 }
  test_set:
    n_tasks: 5
    conditions:
      baseline: { accuracy: 0.40 }
      generic_scaffold: { accuracy: 0.40 }
      v0_self_generated: { accuracy: 0.40 }
      v1_curated: { accuracy: 0.60 }
      v2_optimized: { accuracy: 0.80 }
  dev_test_gap: "v2 dev: 0.80, test: 0.80 — no overfitting observed"
  key_optimization: "Added constraint verification step; test accuracy +20%"
version_history:
  - version: "v1_curated"
    author: "human"
    note: "Initial design based on OR textbook problem-solving procedure"
  - version: "v2_optimized"
    author: "deepseek-chat"
    note: "Added integer feasibility check after dev-set failures showed constraint_missed"
quality_signals:
  verification_type: "exact_match"
  reproducibility: "temperature 0; full determinism not guaranteed on hosted APIs"
limitations:
  - "Demo-level sample size (~10 test questions) — directional evidence only"
  - "Single model validation — cross-model testing required"
  - "Single-turn QA — agent-level task execution not validated"
  - "No statistical significance testing at this sample size"
```

## GDI Ranking Dimensions

If these skills were published on EvoMap, they would be ranked by:

| GDI Dimension | How Our Skills Would Score | Current Limitation |
|---------------|---------------------------|--------------------|
| **Quality** | Test-set accuracy + dev/test split + scaffold control | Small sample, single model |
| **Usage** | Number of task types supported, model compatibility | Only 2 task types, 1 model |
| **Social** | Version history shows human-AI collaboration | Single iteration only |
| **Freshness** | v2 is a recent optimization with documented changelog | Single optimization round |

## From Demo to Marketplace: The Path Forward

### What This Demo Proves

1. Skills can be **structured** in a machine-readable schema
2. Skills can be **validated** against benchmarks with proper dev/test methodology
3. Skills can be **optimized** through human-AI collaborative iteration
4. Skills can carry **evidence** in a format compatible with marketplace distribution
5. Improvement comes from **domain content**, not just structural scaffolding (if scaffold control confirms this)

### What Phase 2 Would Add to Reach "Validated" Evidence Level

1. **Cross-model validation** — test the same skill on 3+ models to establish `supported_models`
2. **Larger samples** — 50+ test questions per task type for statistical power
3. **SkillsBench integration** — validate that skills help in agentic execution, not just QA
4. **Skill composition** — combine multiple skills into Recipes (multi-step workflows)
5. **Community iteration** — allow others to fork, modify, and re-validate skills
6. **Formal statistical testing** — confidence intervals, paired significance tests

### The Research Contribution

The key insight connecting skill optimization to marketplaces:

> **Skills are not prompts. Skills are structured artifacts with evidence.**
>
> A prompt is a one-time instruction. A skill is a versioned, testable, optimizable artifact that carries its own validation data. This distinction is what makes skills potentially suitable for marketplace distribution — they can be compared, ranked, composed, and improved by multiple contributors over time.
>
> Phase 1 demonstrates this concept at demo scale. Phase 2 would validate it at production scale.
