# Problem Framing: Skill Optimization for LLM Agents

## Background

LLM agents often fail not because of weak general capability, but because they lack stable, reusable procedural knowledge for task completion. A **skill** is an explicit, structured behavioral prior that guides how an agent interprets, decomposes, executes, and verifies a task.

SkillsBench (2025) demonstrated that human-curated skills can improve agent performance, but self-generated skills generally do not help. This raises a critical follow-up question: **can we systematically optimize skills through human-AI collaborative iteration?**

## Core Research Question

Given an agent and a task benchmark, can a structured skill optimization loop — where humans design initial skills and AI refines them based on empirical error analysis — produce skills that reliably outperform both no-skill baselines and purely AI-generated skills?

## Project Goal

Build a lightweight skill optimization demo that:

1. Tests four skill conditions (no skill, self-generated, human-curated, AI-optimized) on an ORQA task subset
2. Uses low-cost models (DeepSeek Chat, OpenRouter free tier)
3. Produces interpretable results with error analysis
4. Maps validated skills to marketplace-ready asset formats (EvoMap framing)

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

**RQ1:** Can structured, human-curated skills improve low-cost agent performance on ORQA tasks compared to a no-skill baseline?

**RQ2:** Can AI-driven optimization of human-curated skills (based on empirical error analysis) produce further improvement beyond the initial curated version?

**RQ3:** How do self-generated skills (AI writes from scratch with no human input) compare to human-curated and human-AI optimized skills?

### Secondary

**RQ4:** What types of OR problems benefit most from skill injection, and what types are hindered by it?

**RQ5:** How should effective skills be represented and documented so they can become reusable, verifiable marketplace assets?

### Central Hypothesis

```
v2_optimized > v1_curated > baseline >= v0_self_generated
```

This extends SkillsBench's finding (curated > self-generated) by adding the optimization angle: human-AI collaborative refinement outperforms both pure human design and pure AI generation.

### If the Hypothesis Fails

Negative results are still valuable findings:

- If `v1_curated = baseline`: skills may not help for OR reasoning at this model scale — document why
- If `v0_self_generated > v1_curated`: self-generation may work better than expected for structured domains — analyze what the LLM captured that humans missed
- If `v2_optimized < v1_curated`: the optimization loop may introduce regression — examine whether the optimizer over-corrected
- In all cases, the error analysis and case studies remain publishable contributions

## What This Project Is NOT

- Not a full SkillsBench reproduction via Harbor
- Not a leaderboard submission
- Not a multi-agent system
- Not a marketplace platform implementation

## Scope Boundaries

### In Scope (Phase 1)

- ORQA: 15 questions, 2 task types (linear programming, combinatorial optimization), 4 conditions
- DeepSeek Chat as primary model
- One optimization iteration (v1 -> v2)
- Automated report generation with comparison tables
- Marketplace mapping as conceptual bridge

### Out of Scope (Phase 1)

- SkillsBench task execution (deferred to Phase 2)
- Full Harbor/Docker infrastructure
- Multiple optimization iterations
- Multi-agent architectures
- Actual EvoMap platform integration
- Statistical significance testing (sample too small)

### Phase 2 Extensions (Future Work)

- SkillsBench integration: extract tasks, run with skill injection
- Cross-model comparison (OpenRouter free tier models)
- Multi-round optimization (v2 -> v3 -> v4)
- Automated task-type routing
- Larger ORQA subsets for statistical power

## Success Criteria

| Criterion | Measurable? |
|-----------|-------------|
| Pipeline runs end-to-end on 15 ORQA questions | Yes — produces results for all 4 conditions |
| v1_curated outperforms baseline on at least some tasks | Yes — accuracy comparison |
| v2_optimized shows improvement over v1_curated | Yes — accuracy comparison |
| v0_self_generated performs differently from v1_curated | Yes — accuracy comparison |
| At least 3 success and 3 failure cases are interpretable | Yes — case study in report |
| Error taxonomy is populated with real examples | Yes — error analysis output |
| Skill diffs (v1->v2) have clear changelogs | Yes — optimization output |
| Marketplace cards are produced for effective skills | Yes — YAML artifacts |
