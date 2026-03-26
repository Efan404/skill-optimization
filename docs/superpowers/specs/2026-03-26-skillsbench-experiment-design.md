# SkillsBench Experiment Design Spec

## Status

This document is the **execution-oriented design spec** for the SkillsBench research track introduced in [2026-03-26-skillsbench-protocol-strength-research-spec.md](/Users/efan404/Codes/research/skill-optimization/docs/superpowers/specs/2026-03-26-skillsbench-protocol-strength-research-spec.md).

It translates the high-level research framing into a concrete experimental design.

---

## Objective

Design a SkillsBench study that tests whether a stronger, feedback-driven skill-authoring protocol materially improves over **one-shot self-generated skills** under matched budgets and held-out evaluation.

The design must preserve one core causal boundary:

**the main intervention is at the skill level, not at the agent-system level**

That means the experiment should answer:
- whether self-generated skills are weak because of a weak protocol
- whether optimized self-generated skills close the gap to curated skills

It should **not** answer:
- whether a different planner is better
- whether memory or tool policy changes help
- whether full agent optimization dominates skill optimization

---

## Benchmark Boundary

SkillsBench and ORQA are separate workstreams.

- `ORQA` provides the methodology template and implementation prior
- `SkillsBench` is the claim-bearing benchmark for this study

The SkillsBench design should reuse:
- the five/six-condition comparison structure
- scaffold control
- dev/test isolation
- structured error analysis
- optimization changelogs
- provenance logging

It should **not** import ORQA claims into SkillsBench results.

---

## Study Structure

The SkillsBench study has two layers:

### Layer A: Pilot

Purpose:
- validate task selection
- validate the adapter
- validate that skill-only intervention is technically enforceable
- surface environment/runtime failure modes before the main study

Recommended size:
- `3-5` self-contained SkillsBench tasks

**Recommended pilot shape:** start with exactly `3` tasks, one each from:
- `simple`
- `medium`
- `hard`

This is a good default because it keeps the pilot cheap while still exposing whether the protocol breaks differently across difficulty tiers. It also avoids a biased pilot that only reflects either toy tasks or failure-heavy hard tasks.

Layer A is a systems-and-method check, not the final paper result.

### Layer B: Claim-Bearing Study

Purpose:
- test the protocol-strength hypotheses on a held-out SkillsBench subset

Recommended size:
- expand beyond the pilot subset after the adapter is stable
- use enough tasks that a single task flip does not dominate the conclusion

Layer B is where the main paper claim should come from.

---

## Task Selection Criteria

Only choose SkillsBench tasks that satisfy all of the following:

1. **Self-contained**
- no external API keys
- no hidden proprietary services
- no unstable third-party dependencies

2. **Reproducible locally**
- Docker/Harbor setup works on the project machine
- execution can be repeated with stable scoring

3. **Skill-relevant**
- success plausibly depends on procedural guidance
- not purely a brute-force tool invocation task

4. **Comparable**
- the same runtime, tool access, and environment can be held fixed across conditions

5. **Auditable**
- task success/failure can be logged with enough detail for post-hoc error analysis

### Preferred Diversity

Within the selected subset, prefer tasks that vary across:
- domain
- tool usage pattern
- planning depth
- error modes
- difficulty tier

For the initial pilot, the recommended minimum diversity pattern is:
- `1` simple task
- `1` medium task
- `1` hard task

The goal is not a single narrow task family, but also not a random grab-bag. The selected subset should be interpretable as a coherent pilot or study set.

---

## Experimental Units and Split Logic

The study must define the experimental unit explicitly.

### Preferred Unit

Preferred unit:
- **task instance / episode** if SkillsBench supports multiple comparable instances per task family

This allows:
- `seed` examples for one-shot generation
- `dev` episodes for optimization
- `test` episodes for held-out evaluation

### Fallback Unit

If task-instance granularity is not available, use:
- **task family / task definition** as the held-out unit

In that case:
- use a small subset for pilot/development
- reserve disjoint task families for final evaluation
- be explicit that dev/test split is at the task level, not the instance level

### Hard Rule

The same exact held-out evaluation units must never be used for:
- self-generated skill authoring examples
- optimization feedback
- final claim-bearing test evaluation

---

## Condition Matrix

The main SkillsBench study uses six conditions:

| Condition | Description | Purpose |
|-----------|-------------|---------|
| `baseline` | No skill | Raw agent performance |
| `generic_scaffold` | Structure-only control | Isolate structure from domain content |
| `curated` | Existing human-authored task skill | Human-authored baseline |
| `self_generated_one_shot` | AI-authored skill from limited examples/context only | Recreate the weak self-generated protocol family |
| `self_generated_optimized` | One-shot AI skill improved using dev feedback | Main protocol-strength test |
| `curated_optimized` | Curated skill improved using the same optimization machinery | Symmetric comparison |

### Why Six Conditions

This is the minimum set that can answer the target question cleanly:

- `baseline` tells you whether any skill helps
- `generic_scaffold` controls for prompt structure
- `curated` gives the human-authored reference point
- `self_generated_one_shot` measures the weak protocol baseline
- `self_generated_optimized` tests whether the gap is protocol-driven
- `curated_optimized` prevents asymmetric iterative privilege

---

## Skill Authoring Protocols

### Curated

Source:
- the task's existing `SKILL.md` or a human-authored equivalent that preserves the same role

Constraint:
- treat this as the human-authored starting artifact
- do not silently rewrite it outside the documented optimization path

### Self-Generated One-Shot

Input allowed:
- task description
- tool description
- success criterion
- allowed environment information
- seed examples if the protocol uses them

Input not allowed:
- curated skill text
- dev failure logs
- held-out test evidence

Output:
- one skill artifact produced in one authoring pass

### Self-Generated Optimized

Start from:
- the one-shot self-generated skill

Allowed optimization input:
- dev-only failures
- structured error analysis
- success cases for regression protection

### Curated Optimized

Start from:
- the curated skill

Allowed optimization input:
- the same type of dev-only evidence
- the same optimization budget as the self-generated optimized path

---

## Skill-Only Intervention Boundary

This is the most important design constraint in the study.

### Frozen During the Main Study

Do not change:
- agent runtime
- planner
- tool policy
- memory
- tool inventory
- environment wrapper
- scoring logic
- retry policy, unless the same retry policy applies to every condition

### Allowed to Change

Only the skill artifact may change:
- procedure
- checks
- failure warnings
- ordering of skill steps
- skill wording and organization

If this boundary is violated, the experiment is no longer a clean SkillsBench skill-protocol study.

---

## Budget Controls

The following budgets must be fixed or explicitly disclosed:

### 1. Authoring Budget
- number of one-shot generation attempts
- available context/examples
- token budget

### 2. Optimization Budget
- number of optimization rounds
- number of dev failures shown
- number of success cases shown
- token budget per optimization call

### 3. Skill Budget
- token length
- section count
- number of checklist items
- whether examples are embedded inside the skill

### Matching Principle

The study should avoid a trivial improvement where one condition simply gets much more prompt budget than another. Any meaningful mismatch must be justified and disclosed.

---

## Model Roles and Provenance

The study must separately track:

- `author_model` — writes the initial skill
- `optimizer_model` — revises the skill
- `solver_model` — executes the task using the skill

These may be identical in some runs, but they must be logged as separate fields.

Per run, also log:
- task subset version
- split definition
- runtime version
- tool inventory
- environment hash if available
- seed/dev/test identifiers
- skill token counts
- optimization budget used

---

## Metrics

### Primary Metrics

- **task success rate on held-out test**
- **paired win/loss vs baseline**
- **paired win/loss vs curated**
- **gap reduction**:
  `distance(self_generated_one_shot, curated)` vs `distance(self_generated_optimized, curated)`

### Secondary Metrics

- dev-to-test gap
- runtime failure rate
- extraction / execution failure categories
- cost per successful task
- average step count / trajectory length if available

### Qualitative Outputs

- skill diffs
- changelogs
- failure taxonomy
- case studies for:
  - skill helps
  - skill hurts
  - optimized self-generated closes the gap
  - optimized self-generated still fails in a way curated does not

---

## Success Criteria

### Main Protocol-Strength Signal

The study provides support for the protocol-strength claim if:

1. `self_generated_optimized > self_generated_one_shot` on held-out test
2. the gap between `self_generated_optimized` and `curated` is smaller than the gap between `self_generated_one_shot` and `curated`
3. the improvement cannot be explained purely by generic scaffold or prompt budget inflation

### Stronger Signal

The result is especially strong if:

- `self_generated_optimized` approaches `curated`
- `curated_optimized` improves only modestly while `self_generated_optimized` improves substantially

That pattern would suggest the original weakness is more about the generation protocol than about an inherent ceiling on AI-authored skills.

### Negative Result

The negative result is still meaningful if:

- `self_generated_optimized` remains near `self_generated_one_shot`
- or both remain far below `curated`

That would support the view that the main limitation is not just the one-shot protocol.

---

## Failure Modes to Watch

The pilot and main study should explicitly distinguish:

1. **environment/runtime failure**
- Docker issue
- task setup issue
- network or execution instability

2. **agent-system failure**
- planner misuse
- tool misuse
- unrecoverable execution error

3. **skill failure**
- weak decomposition
- missing guardrails
- poor procedural ordering
- mismatch between skill and task demands

Only the third category should drive the main optimization loop in the skill-only study.

---

## Execution Plan

### Step 1: Task Subset Definition
- identify candidate self-contained SkillsBench tasks
- exclude unstable tasks
- freeze pilot subset

### Step 2: Adapter Validation
- ensure current pipeline can run SkillsBench tasks with the skill-only intervention boundary intact
- confirm logging, provenance, and scoring outputs

### Step 3: Condition Authoring
- prepare curated artifacts
- generate self-generated one-shot artifacts
- build generic scaffold control

### Step 4: Dev Optimization
- run curated and self-generated one-shot on dev
- produce error analysis
- generate `self_generated_optimized` and `curated_optimized`

### Step 5: Held-Out Test
- run all six conditions on held-out test
- compute paired comparisons
- write report from test-first evidence

### Step 6: Interpretation
- decide whether the result supports:
  - protocol weakness
  - persistent human advantage
  - or methodological inconclusiveness

---

## Immediate Implementation Targets

The next concrete implementation tasks should be:

1. create a SkillsBench task-selection note
2. define the split unit and split file format
3. define a SkillsBench run schema with `author_model`, `optimizer_model`, `solver_model`
4. implement or specify the skill-only adapter boundary
5. define the dev-only optimization input package for SkillsBench failures
6. write the report template for six-condition comparison

---

## Out of Scope

This design does not yet cover:
- full agent optimization
- memory/planner ablations
- large-scale Harbor-wide benchmark sweeps
- final paper wording
- marketplace claims

Those should only come after the skill-only SkillsBench study is complete.
