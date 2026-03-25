# Marketplace Mapping: From Benchmark Skills to Reusable Assets

## Context

This document bridges the skill optimization demo to the broader vision of AI agent marketplaces, specifically the EvoMap ecosystem. The goal is to show how validated, versioned skills can be packaged as marketplace-ready assets rather than remaining one-off prompt engineering artifacts.

## EvoMap Concepts

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

The skill optimization approach produces **verifiable assets** because each skill carries:

1. **Structured format** — machine-readable schema, not free-form text
2. **Benchmark evidence** — tested on known tasks with measured accuracy
3. **Error analysis** — documented failure modes and fixes
4. **Version history** — traceable evolution from v0 to v2 with changelogs
5. **Reproducibility metadata** — model, temperature, exact prompts used

This transforms skills from prompt hacks into **publishable, rankable, improvable assets**.

## Marketplace Card Format

Each validated skill produces a marketplace-ready card:

```yaml
asset_name: "or-linear-programming"
asset_type: "capsule"
domain: "operations_research"
supported_models: ["deepseek-chat"]
evidence:
  benchmark: "ORQA"
  n_tasks: 8
  conditions:
    baseline: { accuracy: 0.45 }
    v0_self_generated: { accuracy: 0.40 }
    v1_curated: { accuracy: 0.70 }
    v2_optimized: { accuracy: 0.80 }
  key_optimization: "Added constraint verification step; accuracy +10%"
version_history:
  - version: "v1_curated"
    author: "human"
    note: "Initial design based on OR textbook problem-solving procedure"
  - version: "v2_optimized"
    author: "deepseek-chat"
    note: "Added integer feasibility check after 3/8 failures were constraint_missed"
quality_signals:
  verification_type: "exact_match"
  error_analysis: true
  reproducible: true
```

## GDI Ranking Dimensions

If these skills were published on EvoMap, they would be ranked by:

| GDI Dimension | How Our Skills Score |
|---------------|---------------------|
| **Quality** | Benchmark accuracy + error analysis evidence |
| **Usage** | Number of task types supported, model compatibility |
| **Social** | Version history shows community iteration (human + AI collaboration) |
| **Freshness** | v2 is a recent optimization over v1, with documented changelog |

## From Demo to Marketplace: The Path Forward

### What This Demo Proves

1. Skills can be **structured** in a machine-readable schema
2. Skills can be **validated** against benchmarks with clear metrics
3. Skills can be **optimized** through human-AI collaborative iteration
4. Skills can carry **evidence** that makes them trustworthy for reuse

### What Phase 2 Would Add

1. **Cross-model validation** — test the same skill on different models to establish model compatibility
2. **Cross-benchmark validation** — test on SkillsBench to prove domain generalization
3. **Skill composition** — combine multiple skills into Recipes (multi-step workflows)
4. **Automated publishing** — pipeline that produces marketplace-ready YAML cards automatically
5. **Community iteration** — allow others to fork, modify, and re-validate skills

### The Research Contribution

The key insight connecting skill optimization to marketplaces:

> **Skills are not prompts. Skills are assets.**
>
> A prompt is a one-time instruction. A skill is a versioned, validated, optimizable artifact that carries its own evidence of effectiveness. This distinction is what makes skills suitable for marketplace distribution — they can be compared, ranked, composed, and improved by multiple contributors over time.

This positions skill optimization not as a prompt engineering technique, but as an **asset creation methodology** for the emerging AI agent marketplace ecosystem.
