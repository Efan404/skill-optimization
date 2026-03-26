# Real ORQA Migration and Progressive Autoresearch Integration Spec

## Overview

This spec covers two sequential changes to the skill optimization pipeline:

1. **Step 1-3: Migrate to real ORQA data** — replace constructed questions with the published ORQA dataset, rewrite skills for the model-identification task format, and validate that single-step optimization produces a signal
2. **Step 4: Add autoresearch-inspired search loop** — only if Step 3 confirms a signal, wrap the existing optimizer in a budgeted candidate-generation and selection loop

These are two phases, not one. Step 4 is gated on Step 3 results.

---

## Step 1: Real ORQA Data Migration

### Data Source

- **Repository:** https://github.com/nl4opt/ORQA
- **Files:** `ORQA_test.jsonl` (1,468 instances), `ORQA_validation.jsonl` (45 instances with expert reasoning steps)
- **Dataset label:** "ORQA subset" (source_category 1 — directly from published benchmark)

### Task Format

ORQA questions ask about **optimization model components**, not numerical solutions. Each instance has:
- `CONTEXT`: Natural language description of an optimization problem
- `QUESTION`: Asks about model components (decision variables, constraints, objective, model type, etc.)
- `OPTIONS`: Four multiple-choice answers (A/B/C/D)
- `TARGET_ANSWER`: Correct option letter
- `REASONING`: Expert step-by-step derivation (validation set only)

### Unified Task Type

All questions are classified under a single task type: **`or_model_identification`**

Rationale: ORQA has 11 question subtypes, but at 50 questions total, splitting into 11 categories gives ~4 per type — too few for per-type skills. A unified skill covers the shared capability: "identify optimization model components from NL descriptions."

### Sampling Protocol

**Source allocation:**
- **Seed set (5 questions):** Drawn exclusively from `ORQA_validation.jsonl` (45 instances). These come with expert reasoning steps that inform v1_curated skill design. Seed questions are NEVER evaluated and NEVER seen by the optimizer.
- **Dev set (20 questions):** Drawn from `ORQA_test.jsonl` (1,468 instances). Used for all condition runs, error analysis, and optimization.
- **Test set (25 questions):** Drawn from `ORQA_test.jsonl`. Held out — optimizer never sees these.

**Stratified sampling rule:**
1. From `ORQA_validation.jsonl`: select 5 questions covering at least 3 different question subtypes. Prefer questions with the most detailed expert reasoning.
2. From `ORQA_test.jsonl`: stratified random sample by question subtype. Each subtype should appear at least once in dev if it has ≥ 3 instances. Use fixed random seed (42) for reproducibility.
3. Dev and test are disjoint. Assign to dev first, then test, by alternating within each stratum.

**Frozen after creation:** `split.json` is committed before any experiment runs and never modified.

**No manual cherry-picking:** Selection is by the protocol above. If a question is ambiguous or malformed, exclude it and document the reason in `data/orqa/README.md`.

### Question Format (Adapted)

```json
{
  "id": "orqa_0001",
  "task_type": "or_model_identification",
  "split": "dev",
  "question": "What are the decision activities of the optimization problem?",
  "context": "You are an operations manager at a textile factory...",
  "choices": {
    "A": "Production quantity and shipping schedule",
    "B": "Raw material procurement and inventory levels",
    "C": "Machine allocation and worker assignment",
    "D": "Product pricing and marketing budget"
  },
  "correct_answer": "A",
  "source_category": 1,
  "source_detail": "ORQA test set, instance 42",
  "question_subtype": "decision_activities"
}
```

Note: ORQA instances have a separate `CONTEXT` and `QUESTION` field. Both are preserved.

### Code Changes

| File | Change |
|------|--------|
| `data/orqa/questions.json` | Replace with real ORQA instances |
| `data/orqa/split.json` | New split with ORQA IDs |
| `data/orqa/README.md` | Update: "ORQA subset", source_category 1, sampling protocol |
| `src/task_loader.py` | Add `context` field support. Keep all existing functions. |
| `src/agent_runner.py` | Update prompt templates to include `{context}` before `{question}` |
| `src/run_pipeline.py:39` | Change `TASK_TYPES` from hardcoded list to dynamic: `TASK_TYPES = sorted(set(q["task_type"] for q in load_questions()))` |
| `src/report_generator.py:15` | Same: derive `TASK_TYPES` dynamically from data |
| `src/report_generator.py` | Fix any hardcoded "LP" / "CO" labels in table headers |
| `src/skill_generator.py` | Update `TASK_TYPE_DESCRIPTIONS` for `or_model_identification` |
| `configs/experiments.yaml` | Update task_types |
| `tests/test_task_loader.py` | Update counts, field expectations, remove audit tests for old questions |

### Prompt Template Update

The baseline prompt needs to include the context:

```
You are an expert in operations research. Read the following optimization problem description and answer the question.

**Problem Description:**
{context}

**Question:**
{question}

**Options:**
A) {choice_a}
B) {choice_b}
C) {choice_c}
D) {choice_d}

Think through this step by step, then provide your final answer.

**IMPORTANT:** Your final line MUST be exactly: "ANSWER: X" where X is A, B, C, or D.
```

Scaffold and skill prompts follow the same pattern — just add `{context}` before `{question}`.

---

## Step 2: Rewrite v1_curated + Scaffold

### v1_curated Skill: Target Capability

The unified skill covers **optimization model component identification from natural language**. Specifically:

**What the skill covers:**
- Identifying decision variables / decision activities
- Identifying data parameters (given constants)
- Identifying the objective function and its direction (max/min)
- Identifying constraints and specifications
- Classifying the optimization model type (LP, IP, MILP, NLP, etc.)
- Recognizing relationships between components

**What the skill does NOT cover:**
- Numerical solution of the optimization model
- Code generation for solvers
- Advanced OR techniques (branch-and-bound, simplex internals)

This boundary is important for error analysis — failures outside the skill's scope should be classified as `skill_mismatch`, not `wrong_reasoning`.

### Skill Source

v1_curated is grounded in three published sources (cite in the skill's metadata):

1. **ORQA validation set expert reasoning** — the paper provides step-by-step derivations for 45 instances. These show the expert's problem-solving procedure.
2. **LLMOPT five-element formulation** (ICLR 2025) — universal decomposition: Sets → Parameters → Variables → Objective → Constraints
3. **SkillsBench SKILL.md format** — structured markdown with procedure steps, checks, and common failures

### Skill Structure (6 steps, matching scaffold)

```yaml
name: "or-model-identification"
version: "v1_curated"
source: "curated"
domain: "operations_research"
task_type: "or_model_identification"

when_to_use: "When identifying components of an optimization model from a natural language problem description"
when_not_to_use: "When asked to numerically solve an optimization problem or generate solver code"

preconditions:
  - "A natural language description of an optimization/decision-making scenario is provided"
  - "The question asks about model components, structure, or type — not numerical answers"
  - "Multiple choice options are available"

procedure:
  - step: "Read the problem description and identify the DECISION-MAKER and their GOAL"
    check: "Can you state who is making decisions and what they want to achieve?"
  - step: "Identify all DECISION ACTIVITIES (variables the decision-maker controls)"
    check: "For each activity: what can be changed? What are its possible values (continuous, integer, binary)?"
  - step: "Identify all DATA PARAMETERS (given constants, known quantities)"
    check: "Which numbers/values are fixed inputs, not decisions?"
  - step: "Identify the OBJECTIVE (what to optimize) and its DIRECTION (max or min)"
    check: "Is the objective a function of the decision variables? Is the direction explicit?"
  - step: "Identify all CONSTRAINTS and SPECIFICATIONS (rules, limits, requirements)"
    check: "Re-read the problem. Are there capacity limits, balance equations, logical conditions, or bounds you missed?"
  - step: "Classify the MODEL TYPE based on variable types and function linearity"
    check: "Are variables continuous → LP? Integer → IP? Mixed → MILP? Nonlinear terms → NLP?"

common_failures:
  - "Confusing decision variables with data parameters"
  - "Missing implicit constraints stated indirectly in the problem"
  - "Misclassifying model type due to overlooking integer or nonlinear requirements"
  - "Treating calculated quantities as decision variables"

verification: "Re-read the question. Does your answer specifically address what was asked (variables, constraints, objective, model type, etc.)? Cross-check against the options."
```

### Generic Scaffold

Same structure: 6 steps, 4 common_failures, 3 preconditions. Generic problem-solving content, no OR terms. Token count within +/-15% of v1. Validated before experiments.

---

## Step 3: Validate Single-Step Pipeline on Real ORQA

### Procedure

Run the existing pipeline (`python -m src.run_pipeline --model deepseek`) with the new data and skills.

### Signal Definition (Decidable Criteria)

The following conditions must ALL be met to confirm "signal exists":

1. **v1_curated test accuracy > baseline test accuracy** — the curated skill improves over no-skill baseline on held-out test
2. **v1_curated test accuracy > generic_scaffold test accuracy** — improvement comes from domain content, not just structure
3. **If v2_optimized dev accuracy > v1_curated dev accuracy BUT v2_optimized test accuracy <= v1_curated test accuracy:** flag as overfitting risk, document, but still consider signal present (the optimization loop produced a dev-better candidate, even if it didn't generalize)

**If signal is NOT found:**
- Document the negative result
- Analyze why (error analysis on v1 failures)
- Consider: is the skill targeting the wrong capability? Are the questions too easy/hard for skill differentiation?
- Do NOT proceed to Step 4

**If signal IS found:**
- Proceed to Step 4

---

## Step 4: Autoresearch-Inspired Search Loop (Gated on Step 3)

### Positioning

The auto-search is an **ablation experiment**, not the default pipeline. The main result is still single-step v1/v2. The auto-search answers: "Does budgeted multi-round search find better candidates than single-step optimization?"

### Architecture

**Default pipeline:** unchanged (single-step v1 → v2)
**Experimental branch:** `--auto-optimize` flag activates the search loop

### New Modules

**`src/experiment_log.py`** — Append-only JSONL log

```python
def log_candidate(log_path, entry: dict):
    """Append one entry to results/experiment_log.jsonl.
    Entry: {
        timestamp, round, strategy, parent_skill_hash,
        child_skill_hash, dev_accuracy, dev_wins_vs_parent,
        dev_losses_vs_parent, token_count, accepted, reason
    }
    """

def load_log(log_path) -> list[dict]:
    """Read all entries from the log."""
```

**`src/mutation_proposer.py`** — 3 mutation strategies

```python
STRATEGIES = ["failure_fix", "simplify", "reorder"]

def propose_candidate(client, current_skill, dev_failures, dev_successes,
                      strategy: str, task_type: str) -> tuple[dict, str]:
    """Generate one candidate skill using the specified mutation strategy.
    Returns: (candidate_skill, changelog)
    """
```

Strategy prompts:
- `failure_fix`: current optimizer behavior — "fix the identified failure patterns"
- `simplify`: "Remove any step, check, or common_failure that is not strictly necessary. Make the skill shorter and more focused. Do not add anything new."
- `reorder`: "Reorder the procedure steps so that the checks most likely to catch errors come earlier. Do not add or remove steps."

**`src/auto_optimizer.py`** — Search controller

```python
def auto_optimize(client, base_skill, dev_questions, task_type,
                  max_rounds=3, strategies=STRATEGIES) -> tuple[dict, list[dict]]:
    """
    Budgeted search loop:
    1. Each round: try each strategy, evaluate on dev, apply acceptance rule
    2. Select best candidate
    3. Check stopping criteria
    Returns: (best_skill, search_trajectory)
    """
```

### Acceptance Rule (Constraint-First + Lexicographic Ranking)

**Hard constraints (must all pass):**
- Candidate passes YAML schema validation
- Candidate token count ≤ 2x v1_curated token count
- Only YAML body changed (no prompt wrapper, no evaluator, no scaffold)

**Ranking (lexicographic, applied to candidates that pass hard constraints):**
1. Higher dev accuracy is better
2. If accuracy tied: fewer regressions (questions parent got right, candidate got wrong) is better
3. If still tied: shorter skill (fewer tokens) is better

**Accept if:** candidate ranks higher than current best by this ordering.

### Stopping Criteria (3 layers)

1. **Performance stop:** best_dev_accuracy unchanged for 2 consecutive rounds → stop
2. **Perfect stop:** dev_accuracy == 1.0 → stop
3. **Budget stop:** `max_rounds` reached → stop

### Frozen During Search

- `src/task_loader.py` — no changes
- `src/evaluator.py` — no changes
- `data/orqa/split.json` — no changes
- `data/orqa/questions.json` — no changes (correct answers frozen)
- `src/report_generator.py` scoring logic — no changes
- Generic scaffold definition — no changes
- Prompt wrapper templates — no changes

Only the **skill YAML body** may be mutated.

### Pipeline Integration

```python
# In run_pipeline.py, Phase 3 becomes:
if args.auto_optimize:
    # Phase 3b: Auto-search (experimental branch)
    best_skill, trajectory = auto_optimize(
        client, v1_skill, dev_questions, task_type, max_rounds=3
    )
    # Log trajectory to results/experiment_log.jsonl
else:
    # Phase 3a: Single-step optimization (default)
    v2_skill, changelog = optimize_skill(client, v1_skill, ...)
```

### Experiment Design

**Experiment 1: Single-Step vs Auto-Search**
- Compare on held-out test (run once each):
  - v1_curated
  - v2_single_step (current optimizer)
  - v_best_autosearch
- Report: test accuracy, paired win/loss, search trajectory summary

**Experiment 2: Search Budget Ablation (if time allows)**
- Compare: 1 round, 2 rounds, 3 rounds
- Report: dev accuracy trajectory, diminishing returns

### Claim Scope

**What auto-search results can claim:**
- Whether multi-round search finds dev-better candidates than single-step
- Which mutation strategies are more frequently accepted
- Whether search shows diminishing returns

**What auto-search results CANNOT claim:**
- That auto-search generalizes better (dev set too small for this)
- That the search process is optimal
- Statistical significance

### `research_program.md`

A **policy document** (not an experiment input) that records:
- Allowed modification scope (YAML body only)
- Frozen components list
- Budget limits (max_rounds, strategies)
- Acceptance rule specification
- Stopping criteria
- Claim scope

Purpose: auditability for reviewers. NOT a hidden prompt layer.

---

## Execution Order

```
Step 1 ──> Step 2 ──> Step 3 (run pipeline) ──> Step 4 (only if signal found)
  │                      │
  │                      └─ If no signal: stop, document negative result
  │
  └─ Commit after each step
```

Each step produces a working, testable state. No step depends on Step 4.

---

## Files Changed Summary

### Step 1 (ORQA migration)
- Replace: `data/orqa/questions.json`, `data/orqa/split.json`, `data/orqa/README.md`
- Modify: `src/task_loader.py`, `src/agent_runner.py`, `src/run_pipeline.py`, `src/report_generator.py`, `src/skill_generator.py`, `configs/experiments.yaml`
- Modify: `tests/test_task_loader.py`

### Step 2 (New skills)
- Replace: `skills/orqa/v1_curated/*.yaml`, `skills/generic_scaffold/*.yaml`
- Verify: scaffold token matching

### Step 3 (Validation run)
- No code changes — just run pipeline and inspect results

### Step 4 (Auto-search, conditional)
- Create: `src/experiment_log.py`, `src/mutation_proposer.py`, `src/auto_optimizer.py`, `research_program.md`
- Modify: `src/run_pipeline.py` (add `--auto-optimize` flag)
