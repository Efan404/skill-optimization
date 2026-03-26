# SkillsBench Protocol-Strength Research Spec

## Status

This is the **primary research narrative spec** for the next stage of the project.

It supersedes the earlier ORQA-centered Phase 2 framing as the main claim-bearing direction. ORQA remains important, but its role is narrower: **method validation**, not the final source of evidence for the main paper claim.

---

## Core Research Question

**Does the weak performance of self-generated skills in SkillsBench reflect a fundamental limit of AI skill authoring, or does it mostly reflect a weak one-shot generation protocol?**

This is the target question for the project's next research phase.

The paper-safe version of the claim is:

> We revisit the self-generated condition from SkillsBench with a stronger protocol: development-set feedback, structured error analysis, controlled skill revision, and held-out evaluation. The question is not whether the original paper was "wrong," but whether its one-shot self-generation protocol underestimates the ceiling of AI-authored skills.

---

## Benchmark Roles

The project now uses **two distinct benchmarks with different jobs**:

### ORQA: Method Development / Sanity Check

ORQA is a **pilot benchmark** for building and validating the skill-optimization methodology.

What ORQA can establish:
- The pipeline runs end-to-end
- `baseline / scaffold / self-generated / curated / optimized` is operational
- Dev/test isolation works
- Skill artifacts can be generated, consumed, and revised in a stable loop
- Controls such as scaffold matching, changelog tracking, and error taxonomy are implementable

What ORQA cannot establish:
- Whether SkillsBench's `self-generated` protocol is too weak
- Whether iterative skill optimization changes outcomes in agentic task execution
- Whether agent skill authoring, rather than QA prompting, is the real source of improvement

### SkillsBench: Main Research Benchmark

SkillsBench is the **claim-bearing benchmark** for the next stage.

It is where the project tests whether:
- one-shot self-generated skills are weak because of protocol weakness
- optimized self-generated skills can substantially close the gap to curated skills
- the key intervention is at the skill level, not a broader agent-system rewrite

**Important boundary:** ORQA is not embedded into SkillsBench, and SkillsBench is not treated as "Phase 2 ORQA." They are separate benchmarks connected by a shared methodology.

---

## Research Logic

The project proceeds in three stages:

### Stage 1: ORQA Skill Optimization

Purpose: validate the method.

This stage is successful if it shows that the following are technically and methodologically sound:
- skill generation and optimization can be run with controlled artifacts
- the evaluator, report, and provenance machinery work
- dev evidence is separated from held-out test evidence
- scaffold control isolates structure from domain content

This stage is **not** the main evidence for the paper's final claim about SkillsBench.

### Stage 2: SkillsBench Skill-Level Optimization

Purpose: answer the main research question.

This is the central experiment. The intervention must be **skill-only**:
- keep agent runtime fixed
- keep solver model fixed per condition set
- keep tools fixed
- keep task environment fixed
- keep evaluation fixed
- only change the skill artifact and its revision process

This stage asks whether the performance gap between curated and self-generated skills is caused by:
- weak skill content, or
- a weak generation protocol

### Stage 3: Agent Optimization

Purpose: future work after the main claim is settled.

This stage may modify planner behavior, tool policy, memory, retry logic, or other agent-level components. It is explicitly **not** part of the direct SkillsBench protocol-strength claim.

If Stage 3 starts too early, the project will lose causal clarity.

---

## Main Hypotheses

The project's main hypotheses on SkillsBench are:

1. **H1:** One-shot self-generated skills are weaker than curated skills under matched evaluation conditions.
2. **H2:** Optimized self-generated skills outperform one-shot self-generated skills when given controlled dev-set feedback.
3. **H3:** If optimized self-generated skills approach curated skills, the original one-shot protocol likely underestimates AI skill-authoring capacity.
4. **H4:** If optimized self-generated skills still remain clearly below curated skills, the evidence favors the view that high-quality skills still depend on human-authored procedural compression.

These hypotheses are about **protocol strength**, not about whether prior authors "used AI badly."

---

## SkillsBench Experimental Design

### Core Comparison

The minimum claim-bearing comparisons on SkillsBench should be:

| Condition | Role |
|-----------|------|
| baseline | No skill |
| generic_scaffold | Structure-only control |
| curated | Existing task skill / human-authored skill |
| self_generated_one_shot | One-shot AI-authored skill |
| self_generated_optimized | AI-authored skill improved using dev feedback |
| curated_optimized | Human-authored skill improved using the same optimization machinery |

The last two conditions are both important:
- `self_generated_optimized` answers whether protocol strengthening helps AI-authored skills
- `curated_optimized` prevents an asymmetric comparison where only one side gets iterative refinement

### Intervention Boundary

For the main study, only the **skill artifact** may change.

Not allowed during the core claim-bearing experiment:
- changing planner logic
- adding memory
- changing tool policy
- changing tool availability
- changing environment wrappers
- switching evaluation definitions mid-study

Allowed:
- changing skill content
- changing skill organization
- changing skill checks / warnings / failure modes
- revising the skill under a fixed optimization budget

---

## Hard Controls

The following controls are mandatory for a fair SkillsBench study:

### 1. Model Separation

Track separately:
- the model that writes the skill
- the model that optimizes the skill
- the model that executes the task with the skill

These may be the same model in some runs, but they must never be conflated in reporting.

### 2. Budget Symmetry

Curated and self-generated paths must have matched or explicitly disclosed budgets:
- number of optimization rounds
- context budget
- token budget
- skill count / module count
- access to failure analysis

### 3. Artifact Contract Symmetry

All compared skills must share:
- the same skill schema
- the same injection point
- the same wrapper protocol
- the same evaluator

Otherwise the experiment becomes a prompt-architecture comparison instead of a skill-authoring comparison.

### 4. Dev/Test Isolation

Optimization is dev-only.

The final claims must come from held-out test tasks only. Dev performance may be used to explain optimization behavior, but not to support the main result.

---

## Relationship to Existing ORQA Pipeline

The ORQA pipeline remains useful because it already provides:
- a five-condition comparison template
- scaffold control
- structured error analysis
- optimized-skill changelogs
- provenance and run isolation

The intended bridge is:

**reuse the methodology, not the benchmark**

That means:
- ORQA results can justify the pipeline design
- ORQA results cannot be used as the main evidence for a SkillsBench claim
- SkillsBench should be treated as a new benchmark-specific experimental workstream

---

## What the Main Paper Can Claim

If Stage 2 succeeds, the paper may claim something like:

> On SkillsBench, the gap between curated and self-generated skills is not fully explained by skill content alone; the generation protocol itself matters. A feedback-driven optimization protocol materially improves AI-authored skills relative to one-shot self-generation under matched budgets and held-out evaluation.

If Stage 2 fails, the paper may still claim:

> Under controlled optimization budgets, self-generated skills remain meaningfully weaker than curated skills on SkillsBench, suggesting that the main limitation is not merely one-shot protocol weakness.

Both are meaningful outcomes.

---

## Immediate Next Actions

1. Freeze the ORQA workstream as methodology-validation evidence, not the main claim.
2. Define the SkillsBench task subset for the claim-bearing study.
3. Write the SkillsBench condition matrix with explicit skill-only intervention boundaries.
4. Define the symmetric optimization budget for `self_generated` and `curated`.
5. Add provenance fields that distinguish skill-author, skill-optimizer, and task-solver models.
6. Run a small pilot on 3-5 self-contained SkillsBench tasks before scaling up.

---

## Out of Scope for This Spec

This spec does not define:
- a full agent-optimization research program
- a Harbor-wide reproduction of all SkillsBench tasks
- claims about marketplace deployment
- cross-benchmark statistical meta-analysis

Those may come later, but they are not the primary objective of this stage.
