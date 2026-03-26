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
- **IMPORTANT framing note:** Our dev/test split is an **internal re-split of the published ORQA data**, NOT the canonical ORQA public-test evaluation. Results should never be compared directly to Table 2 of the ORQA paper. All reporting must state: "Evaluated on an internal 20-dev/25-test split of ORQA instances, not the official ORQA test benchmark."

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
- **Seed set (5 questions):** Drawn exclusively from `ORQA_validation.jsonl` (45 instances). Used ONLY for v0 skill generation (the LLM sees these 5 examples). Seed questions are NEVER evaluated and NEVER seen by the optimizer.
- **Dev set (20 questions):** Drawn from `ORQA_test.jsonl` (1,468 instances). Used for all condition runs, error analysis, and optimization.
- **Test set (25 questions):** Drawn from `ORQA_test.jsonl`. Held out — optimizer never sees these.

**Knowledge source boundary (v0 vs v1):**
- **v0_self_generated:** The LLM sees ONLY the 5 seed questions (with their context, question, and options — but NOT the expert reasoning). It generates a skill from these examples alone.
- **v1_curated:** The researcher may reference ALL 45 validation instances and their expert reasoning steps when designing the skill. This is explicitly disclosed in the methodology section. The rationale: v1 represents "human expertise informed by domain literature", not "few-shot example adaptation."
- This asymmetry is intentional and must be stated in the report: "v1 was designed with access to 45 expert reasoning traces from the ORQA validation set; v0 was generated from 5 seed examples without expert reasoning."

**Stratified sampling rule (fully deterministic, no researcher discretion):**
1. From `ORQA_validation.jsonl`: group by question subtype, sort each group by REASONING field length descending (longer reasoning = more detailed procedure), take the top instance from each subtype until 5 are selected. If fewer than 5 subtypes exist, take the next-longest from already-sampled subtypes. Ties broken by instance order in the file.
2. From `ORQA_test.jsonl`: stratified random sample by question subtype using fixed random seed (42). Each subtype with ≥ 3 instances gets at least 1 representative in dev. Remaining quota filled proportionally.
3. Dev and test are disjoint. Within each stratum, assign by alternating: first instance to dev, second to test, third to dev, etc.

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

### Skill Internal Architecture: Three-Layer Design

The v1 skill must go beyond a sequential checklist. A pure checklist (read → find variables → find constraints → classify) is structurally similar to the generic scaffold and won't differentiate enough to pass Gate 1. The key value of a domain-specific skill is **archetype priors** — knowing that "assign workers to tasks" triggers an assignment model skeleton.

**Design principle:** One unified YAML skill, internally organized in three layers. NOT a multi-skill router — that would introduce a prompt-architecture confound.

**Layer 1: Meta Framework (short)**
- Determine what the question is asking about (variables? constraints? model type?)
- Map the scenario to an OR archetype
- Keep this layer brief — it overlaps with scaffold and shouldn't be the differentiator

**Layer 2: Archetype Library (main body — this is where v1's value lives)**
- Embedded within the unified skill as a reference section
- Covers common OR problem archetypes with trigger cues and expected model skeletons:
  - **Assignment/Matching:** "assign X to Y", binary variables, one-to-one constraints
  - **Routing/Network:** "route through", "shortest path", flow variables, flow conservation
  - **Scheduling/Timetabling:** "schedule tasks", "time slots", sequencing variables, precedence constraints
  - **Blending/Mixing:** "mix ingredients", "blend", continuous proportions, quality specifications
  - **Facility Location:** "open/close", binary location decisions + continuous allocation
  - **Production Planning/Lot-sizing:** "produce over periods", inventory balance equations
  - **Transportation:** "ship from... to...", supply/demand balance, flow capacity
- For each archetype: trigger cues, likely variable types, likely objective family, likely constraint families, common confusions

**Layer 3: High-Precision Local Rules (few, precise, high-confidence)**
- Only a small number of very reliable patterns:
  - "assign ... to ..." → assignment archetype
  - "maximize profit / minimize cost" → objective direction
  - "at most / at least / exactly" → constraint polarity (≤, ≥, =)
  - Binary indicators ("whether to open/close") → model has integer variables → MILP
- Must be few, precise, and explainable — not keyword tricks

**Research constraint:** The skill's external structure (number of procedure steps, common_failures, preconditions) must still match the scaffold for fair comparison. The layered organization is in the **content** of the steps, not the structure.

### Skill Procedure (4 stages, internally layered)

```
Stage A: Determine Question Target
  → What component is the question asking about?
  → (variables / parameters / objective / constraints / model type / relationship)

Stage B: Map Scenario to Archetype (Layer 2 — core value)
  → Read context, identify trigger cues
  → Match to OR archetype (assignment, routing, scheduling, blending, etc.)
  → Activate archetype-specific priors for expected variables, objective, constraints

Stage C: Instantiate Model Skeleton (using archetype priors)
  → Elements/entities (sets)
  → Decision variables (guided by archetype expectations)
  → Parameters (given constants)
  → Objective (direction + participating variables/parameters)
  → Constraints (type, LHS meaning, RHS, applied-on)

Stage D: Answer Against Options
  → Focus only on the component the question asks about
  → Eliminate options that contradict the problem text
  → Prefer options with direct textual support over plausible-sounding alternatives
```

### Why This Matters for the Experiment

- If v1 is just a checklist → v1 ≈ scaffold → Gate 1 fails → no autoresearch
- If v1 has archetype priors → v1 provides genuinely different guidance than scaffold → measurable signal possible
- The scaffold has the SAME structure (4 stages) but NO archetype content → this isolates whether the improvement comes from domain-specific priors

### Generic Scaffold

Same external structure: same number of procedure steps, same number of common_failures, same number of preconditions. Token count within +/-15% of v1. Content is purely generic problem-solving — same 4-stage flow (determine target → analyze context → extract information → answer against options) but with NO OR terminology, NO archetype library, NO domain-specific trigger cues. Validated before experiments.

---

## Step 3: Validate Single-Step Pipeline on Real ORQA

### Procedure

Run the existing pipeline (`python -m src.run_pipeline --model deepseek`) with the new data and skills.

### Signal Definition (Two-Layer Gating)

**Gate 1: Project continues (skill has value)**

Both conditions must be met:
1. **v1_curated test accuracy > baseline test accuracy** — the curated skill improves over no-skill baseline
2. **v1_curated test accuracy > generic_scaffold test accuracy** — improvement comes from domain content, not just structure

If Gate 1 fails: document negative result, analyze why, do NOT proceed to Step 4.

**Gate 2: Auto-search is warranted (optimization loop is not purely overfitting)**

Gate 1 must pass AND at least one of these must hold:
- **v2_optimized test accuracy >= v1_curated test accuracy** — single-step optimization at least didn't hurt on test
- **v2_optimized test accuracy < v1_curated test accuracy BUT the gap is ≤ 1 question** — minor regression, still worth exploring whether a more controlled search can do better

If Gate 2 fails (i.e., single-step v2 significantly regresses on test):
- Document the overfitting finding
- Do NOT run auto-search as a "capability enhancement" branch
- Optionally: reposition Step 4 as an **overfitting diagnosis** experiment — "Can a constrained search with regression penalty avoid the overfit that single-step optimization showed?" This must be explicitly re-framed in the report.

**If both gates pass:** Proceed to Step 4 as designed (auto-search as ablation).

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
