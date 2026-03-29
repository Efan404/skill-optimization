# SkillsBench Memento-Inspired Optimization Spec

**Status:** proposed execution and research spec for the SkillsBench workstream.

This document defines a bridge-claim design for SkillsBench:

- the **main claim** remains a `protocol-strength` claim about skill optimization
- the **supporting contribution** is a Memento-inspired offline optimization system for writing, revising, and tracking skills

This spec extends, but does not replace, the existing SkillsBench research framing in [2026-03-26-skillsbench-protocol-strength-research-spec.md](/Users/efan404/Codes/research/skill-optimization/docs/superpowers/specs/2026-03-26-skillsbench-protocol-strength-research-spec.md) and [2026-03-26-skillsbench-experiment-design.md](/Users/efan404/Codes/research/skill-optimization/docs/superpowers/specs/2026-03-26-skillsbench-experiment-design.md).

---

## 1. Objective

Design a SkillsBench study that borrows the useful ideas of Memento-Skills without collapsing the causal boundary between:

- `skill optimization`
- `agent-system optimization`

The goal is to answer:

> Does a stronger, feedback-driven skill optimization protocol materially improve AI-authored skills on SkillsBench under matched budgets and held-out evaluation?

The system contribution is explicitly secondary:

> Can a Memento-inspired offline optimizer reliably produce useful skill revisions, track utility, and maintain auditable skill evolution history?

---

## 2. Claim Structure

### Main Claim

The claim-bearing result is a **protocol-strength claim**:

- `self_generated_optimized` should outperform `self_generated_one_shot`
- the gap between `self_generated_optimized` and `curated` should shrink under a stronger optimization protocol

This is the core paper-safe conclusion.

### Supporting Claim

The supporting contribution is a **systems claim**:

- we construct a Memento-inspired offline optimization system that performs skill attribution, skill revision, utility tracking, and mutation gating
- this system improves the quality and auditability of skill optimization without entering the claim-bearing test runtime

### Hard Priority Rule

If the system contribution and the protocol-strength claim conflict, the protocol-strength claim takes priority.

The study must remain interpretable even if the optimization system is only partially mature.

---

## 3. Core Causal Boundary

The core rule is unchanged:

**the main intervention is at the skill artifact level, not at the runtime-agent level**

Therefore:

- claim-bearing evaluation must use a **frozen executor runtime**
- the injected **skill artifact** is the only object that changes across the main experimental conditions

### Frozen During Claim-Bearing Evaluation

Do not change:

- planner logic
- memory
- tool inventory
- tool policy
- retry policy
- task wrapper
- verifier or evaluator
- online router behavior
- online write-back behavior

### Allowed To Change

Only the skill artifact may change:

- procedure
- checks
- warnings
- common failures
- organization and wording
- supporting validation instructions inside the skill

### Hard Rule

No online skill mutation during claim-bearing evaluation.

All optimization outputs must be frozen into static skill artifacts before held-out test execution.

---

## 4. Relationship To Memento-Skills

This work borrows several ideas from Memento-Skills:

- externalized skill memory
- failure attribution before revision
- utility tracking per skill
- patch-vs-replace decisions
- revision gating to prevent regressions

This work does **not** directly import the full Memento runtime into the claim-bearing experiment.

### Why

Memento-Skills optimizes a larger object:

- retrieve a skill
- execute it
- reflect on failure
- attribute utility
- rewrite or replace the skill
- write back into the skill library

That is a valuable design for building self-improving agents, but it is a broader intervention than this study can cleanly claim.

### Allowed Bridge

Memento-inspired mechanisms are allowed only in:

- skill authoring
- dev-time optimization
- proposal generation
- revision selection
- audit logging

They are not allowed as part of the online test-time executor.

---

## 5. Study Structure

The study has two layers.

### Layer A: Pilot / Systems Validation

Purpose:

- validate the artifact contract
- validate skill injection
- validate the dev-time optimizer
- validate logging, attribution, and mutation gating

Recommended initial tasks:

- `overfull-hbox`
- `db-wal-recovery`
- `feal-differential-cryptanalysis`

This layer is not claim-bearing. It is a systems-and-method check.

### Layer B: Claim-Bearing Study

Purpose:

- test whether optimized AI-authored skills improve over one-shot AI-authored skills
- test whether stronger protocol narrows the gap to curated skills

Recommended expansion:

- enlarge the task family set after the pilot stabilizes
- keep the runtime, evaluator, and artifact contract unchanged

---

## 6. Experimental Unit And Split Logic

### Preferred Unit

Preferred unit:

- `task instance / episode`

This supports:

- seed examples
- dev episodes
- held-out test episodes

### Fallback Unit

If task-instance granularity is unavailable:

- use `task family` as the split unit

Then:

- reserve some task families for development
- reserve disjoint task families for held-out evaluation
- state explicitly that the split is family-level rather than episode-level

### Hard Rule

The same held-out evaluation unit must never be used for:

- self-generated skill authoring input
- optimization feedback
- revision gating
- final claim-bearing evaluation

---

## 7. Condition Matrix

The study uses six conditions:

| Condition | Role |
|-----------|------|
| `baseline` | No skill |
| `generic_scaffold` | Structure-only control |
| `curated` | Human-authored task skill |
| `self_generated_one_shot` | One-shot AI-authored skill |
| `self_generated_optimized` | One-shot AI skill revised using dev-time optimizer |
| `curated_optimized` | Curated skill revised using the same dev-time optimizer |

### Interpretation

- `baseline` measures raw executor performance
- `generic_scaffold` isolates structural prompting from task content
- `curated` is the human reference point
- `self_generated_one_shot` reproduces the weak protocol baseline
- `self_generated_optimized` tests protocol strengthening
- `curated_optimized` ensures symmetric iterative privilege

### System Role Declaration

For every run, log three separate roles:

- `skill_author`
- `skill_optimizer`
- `task_executor`

These roles may use the same model in some runs, but they must never be conflated in reporting.

---

## 8. Memento-Inspired Offline Optimizer Contract

The optimizer is an **offline / dev-time skill revision service**.

Its input is:

- current skill artifact
- task description
- tool description
- verifier contract
- dev execution traces
- dev failure labels
- dev success cases for regression protection
- skill utility ledger

Its output is:

- revised static skill artifact
- revision rationale
- failure attribution summary
- changelog
- acceptance recommendation

### Allowed Operations

- reorder procedure steps
- add or remove checks
- strengthen guardrails
- add common failures
- simplify or delete misleading content
- revise one failure-prone module
- propose `replace skill` when patching is no longer justified

### Forbidden Operations

- changing executor runtime
- changing tools or tool policy
- changing evaluator or verifier
- changing retry policy
- changing memory or online router behavior
- online skill mutation during held-out test execution
- per-test dynamic skill generation

### Failure Attribution First

Every revision proposal must first declare a primary cause:

- `routing_mismatch`
- `missing_procedure`
- `wrong_abstraction`
- `verification_weakness`
- `constraint_mismatch`
- `output_format_weakness`

No rewrite is valid without explicit attribution.

### Patch vs Replace Rule

- `patch` when the skill still has useful utility and failures are local
- `replace` when utility remains low across rounds or the abstraction is fundamentally wrong

---

## 9. Artifact Contract

Each skill version is a versioned object, not an untracked prompt blob.

### Required Files Per Skill Version

- `skill.md`
  The only artifact injected into the claim-bearing executor.

- `metadata.json`
  Must include:
  - `skill_id`
  - `parent_skill_id`
  - `condition_type`
  - `author_type`
  - `author_model`
  - `optimizer_model`
  - `task_binding`
  - `created_at`
  - `token_count`

- `ledger.json`
  Must include:
  - `dev_uses`
  - `dev_successes`
  - `failure_counts_by_type`
  - `last_edited_round`
  - `accepted_mutations`
  - `rejected_mutations`

- `changelog.md`
  Human-readable record of:
  - what changed
  - why it changed
  - which failure type it targeted
  - what risks remain

### Optimization Run Bundle

Every optimization round should also emit a bundle containing:

- input skill version id
- input dev evidence ids
- failure attribution report
- candidate revised skill
- mutation gate results
- final accept/reject decision

### Hard Rule

Claim-bearing analysis must report both final performance and skill evolution provenance.

Unlogged skill mutations are invalid artifacts.

---

## 10. Logging And Provenance

Each run must preserve enough detail to answer:

- which skill was used
- where it came from
- what optimizer touched it
- what evidence it saw
- why a revision was accepted or rejected

### Required Provenance Fields

- benchmark
- task family
- split type
- condition
- executor runtime version
- task executor model
- skill author model
- skill optimizer model
- input skill id
- output skill id
- parent skill id
- optimizer round number
- mutation decision
- verifier outcome
- failure mode labels

---

## 11. Evaluation Logic

Evaluation happens at three levels:

### 11.1 Task Outcome

Measure:

- verifier pass rate
- completion under task timeout
- correct output format

### 11.2 Failure Mode

For failed runs, assign one or more failure labels:

- `tool_misuse`
- `wrong_procedure`
- `missing_substep`
- `verification_missing`
- `abstraction_mismatch`
- `constraint_violation`
- `format_output_error`
- `hallucinated_operation`

### 11.3 Skill Revision Quality

A revision is judged by:

- whether it improves the target failure mode
- whether it preserves existing success cases
- whether it stays within complexity budget
- whether its rationale is coherent and specific

---

## 12. Mutation Gate

Every candidate skill revision must pass a dev-time gate before acceptance.

### Minimum Gate Requirements

1. It improves the targeted failure mode on dev evidence.
2. It does not cause clear regression on protected success cases.
3. It remains within predefined token and complexity budget.
4. It includes a changelog that states:
   - target failure mode
   - intended repair
   - expected tradeoff

### Gate Outcomes

- `accept`
- `reject`
- `rollback`

### Recommended Additional Gate

Where task format permits, run synthetic or sampled regression checks before accepting the mutation.

---

## 13. Acceptance Rules And Stopping Policy

### Revision Acceptance Rule

A candidate skill revision is accepted only if:

1. It shows net gain on the targeted failure type.
2. It does not introduce substantial regression on prior successes.
3. It stays within artifact budget.
4. The change rationale is specific and auditable.

### Stopping Policy

To avoid search over noise:

- maximum `2-3` optimization rounds per skill
- stop after `2` consecutive no-gain rounds
- rollback on clear regression

### Optimize Until Evidence Plateaus

The stopping criterion is evidence-based, not idea-based.

The optimizer should stop when measured improvement plateaus, not when it can no longer produce new edits.

---

## 14. Main Hypotheses

### Main Protocol-Strength Hypotheses

- `H1`: `self_generated_one_shot < curated`
- `H2`: `self_generated_optimized > self_generated_one_shot`
- `H3`: `self_generated_optimized` closes part of the gap to `curated`
- `H4`: `curated_optimized` provides a symmetric upper reference and may remain above `self_generated_optimized`

### Supporting Systems Hypotheses

- `S1`: failure attribution is stable enough to guide targeted revision
- `S2`: mutation gating filters out regressions
- `S3`: utility ledger trends correlate with accepted revisions
- `S4`: patch-vs-replace decisions are more stable than unconditional patching

---

## 15. Reporting Template

For each task family, report:

- `baseline`
- `generic_scaffold`
- `curated`
- `self_generated_one_shot`
- `self_generated_optimized`
- `curated_optimized`

### Required Tables

1. **Outcome Table**
   - pass rate
   - verifier success
   - timeout / format failure rate

2. **Skill Evolution Table**
   - initial skill id
   - revision count
   - accepted mutations
   - rejected mutations
   - final skill id

3. **Failure Distribution Table**
   - failure counts by type per condition

4. **Attribution Table**
   - optimization round
   - target failure
   - proposed change
   - accepted or rejected
   - observed effect

### Reporting Rule

Final claims must be based on held-out test only.

Dev metrics may explain optimizer behavior, but may not be used as main evidence.

---

## 16. Immediate Roadmap

### Phase A: Artifact And Runtime Freeze

Goals:

- define the static skill artifact contract
- freeze the claim-bearing executor runtime
- make skill injection stable across all six conditions

Deliverables:

- unified `skill.md` format
- metadata and ledger contract
- frozen runtime definition

### Phase B: Offline Optimizer MVP

Goals:

- build the minimum useful optimizer
- support attribution, patch, replace, and changelog generation
- add mutation gate and ledger updates

Explicit non-goals:

- online write-back
- dynamic test-time routing changes
- full self-evolving runtime integration

### Phase C: Three-Task Pilot

Run the six-condition matrix on:

- `overfull-hbox`
- `db-wal-recovery`
- `feal-differential-cryptanalysis`

Validate:

- artifact correctness
- optimizer stability
- mutation gate behavior
- protocol-strength signal

### Phase D: Claim-Bearing Expansion

After the pilot stabilizes:

- add more SkillsBench task families
- preserve the same runtime
- preserve the same optimizer budget
- preserve the same artifact contract

Scale sample size without changing the study logic.

---

## 17. Summary

This spec defines a bridge-claim design:

- the **main experiment** remains a controlled skill-optimization study
- the **Memento-inspired system** is used as an offline optimization backend, not as the online claim-bearing runtime

The key research discipline is simple:

> Use the Memento-Skills idea to improve how skills are written and revised, without letting broader agent-system changes contaminate the main SkillsBench claim.
