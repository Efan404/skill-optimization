# Problem Framing: Skill Optimization for LLM Reasoning

## Background

LLMs often fail not because of weak general capability, but because they lack stable, reusable procedural knowledge for task completion. A **skill** is an explicit, structured behavioral prior that guides how an LLM interprets, decomposes, executes, and verifies a task.

SkillsBench (2025) demonstrated that human-curated skills can improve agent performance, but self-generated skills generally do not help. This raises a critical follow-up question: **can we systematically optimize skills through human-AI collaborative iteration?**

## Core Research Question

Given an LLM and a task benchmark, can a structured skill optimization loop — where humans design initial skills and AI refines them based on empirical error analysis — produce skills that show directional improvement over both no-skill baselines and purely AI-generated skills?

## Project Goal

Build a lightweight skill optimization demo that:

1. Tests five prompting conditions (no skill, generic scaffold, self-generated skill, human-curated skill, AI-optimized skill) on an ORQA task subset
2. Uses low-cost models (DeepSeek Chat, OpenRouter free tier)
3. Uses proper dev/test split to validate generalization of optimized skills
4. Produces interpretable results with error analysis
5. Projects how validated skills could be organized as marketplace assets (EvoMap framing)

## Scope of Claims

**What Phase 1 can demonstrate:**
- Whether structured procedural prompting improves LLM reasoning on OR multiple-choice problems
- Whether human-AI collaborative skill refinement produces directional improvement over initial designs
- Whether domain-specific skill content outperforms generic scaffolding of equal length

**What Phase 1 cannot claim:**
- That this generalizes to agentic task execution (Phase 1 is single-turn QA, not multi-step agent tasks)
- That skills are "reliably superior" (sample size supports directional evidence only)
- That marketplace cards represent validated production-ready assets (they are demo metadata showing the schema)

The connection to agent skill optimization and marketplace assets is positioned as **motivation and future direction**, not as a conclusion proven by this demo.

## Why ORQA as Primary Benchmark

| Criterion | ORQA |
|-----------|------|
| **Task format** | Multiple-choice QA — clean input/output, deterministic evaluation |
| **Domain** | Operations research — structured, expert-level reasoning |
| **Skill fit** | OR problems have well-defined solving procedures that map naturally to skills |
| **Evaluation** | Exact match on answer letter — no subjective rubrics |
| **Feasibility** | No Docker/Harbor infrastructure required |

SkillsBench provides important framing context (the curated vs self-generated finding) but is deferred to Phase 2 due to its Docker/Harbor infrastructure requirements.

## Research Questions

### Primary

**RQ1:** Can structured, human-curated skills improve low-cost LLM performance on ORQA tasks compared to a no-skill baseline?

**RQ2:** Can AI-driven optimization of human-curated skills (based on dev-set error analysis) produce further improvement that generalizes to a held-out test set?

**RQ3:** How do self-generated skills (AI writes from scratch with no human input) compare to human-curated and human-AI optimized skills?

**RQ4:** Does improvement come from domain-specific skill content, or merely from longer/more structured prompting? (Tested via generic scaffold control.)

### Secondary

**RQ5:** What types of OR problems benefit most from skill injection, and what types are hindered by it?

**RQ6:** How should effective skills be represented and documented so they could become reusable assets in a marketplace context?

### Central Hypothesis

```
v2_optimized > v1_curated > generic_scaffold >= baseline >= v0_self_generated
```

This extends SkillsBench's finding (curated > self-generated) by adding:
- The **optimization angle**: human-AI collaborative refinement outperforms initial human design
- The **scaffold control**: improvement comes from domain content, not just structured formatting

### If the Hypothesis Fails

Negative results are still valuable findings:

- If `v1_curated = baseline`: skills may not help for OR reasoning at this model scale — document why
- If `generic_scaffold >= v1_curated`: the value is in structured prompting, not domain-specific skill content — this itself is a publishable finding
- If `v0_self_generated > v1_curated`: self-generation may work better than expected for structured domains — analyze what the LLM captured that humans missed
- If `v2_optimized < v1_curated`: the optimization loop may introduce regression — examine whether the optimizer over-corrected
- If `v2_optimized` improves on dev but not test: overfitting to dev set — document the gap
- In all cases, the error analysis and case studies remain publishable contributions

## What This Project Is NOT

- Not a full SkillsBench reproduction via Harbor
- Not a leaderboard submission
- Not a multi-agent system
- Not a marketplace platform implementation
- Not a statistically powered study — it is a methodology demo with directional evidence

## Scope Boundaries

### In Scope (Phase 1)

- ORQA: ~25 questions, 2 task types, 5 conditions, proper dev/test split
- Generic scaffold control to isolate prompt-length confound
- DeepSeek Chat as primary model
- One optimization iteration (v1 -> v2) using dev-set evidence only
- Paired win/loss and accuracy delta reporting
- Marketplace mapping as conceptual projection

### Out of Scope (Phase 1)

- SkillsBench task execution (deferred to Phase 2)
- Full Harbor/Docker infrastructure
- Multiple optimization iterations
- Multi-agent architectures
- Actual EvoMap platform integration
- Formal statistical significance testing (sample supports directional evidence only)
- Agentic task execution claims

### Phase 2 Extensions (Future Work)

- SkillsBench integration: extract tasks, run with skill injection, validate agent-level claims
- Cross-model comparison (OpenRouter free tier models)
- Multi-round optimization (v2 -> v3 -> v4) with larger dev sets
- Automated task-type routing
- Larger ORQA subsets for statistical power and confidence intervals
- Upgrade marketplace cards from "demo" to "validated" evidence level

## Success Criteria

| Criterion | Measurable? |
|-----------|-------------|
| Pipeline runs end-to-end with proper dev/test split | Yes — produces results for all 5 conditions on both sets |
| v1_curated shows directional improvement over baseline on test set | Yes — paired win/loss + accuracy delta |
| v1_curated outperforms generic_scaffold on test set | Yes — isolates domain content vs structure |
| v2_optimized shows directional improvement over v1 on test set | Yes — paired win/loss + accuracy delta |
| Dev-to-test gap for v2 is reported as descriptive signal | Yes — report raw dev vs test accuracy; do not treat as pass/fail criterion at this sample size |
| At least 3 success and 3 failure cases are interpretable | Yes — case study in report |
| Root cause taxonomy is populated with real examples | Yes — error analysis output |
| Skill diffs (v1->v2) have clear changelogs | Yes — optimization output |
| Demo marketplace cards are produced with proper caveats | Yes — YAML artifacts |
