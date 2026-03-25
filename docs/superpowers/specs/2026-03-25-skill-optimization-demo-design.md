# Skill Optimization Demo — Design Spec

## 1. Problem Framing

### Background

LLMs often fail not because of weak general capability, but because they lack stable, reusable procedural knowledge for task completion. A **skill** is an explicit, structured behavioral prior that guides how an LLM interprets, decomposes, executes, and verifies a task.

SkillsBench (2025) demonstrated that human-curated skills can improve agent performance, but self-generated skills generally do not help. This raises a critical follow-up question: **can we systematically optimize skills through human-AI collaborative iteration?**

### Core Research Question

Given an LLM and a task benchmark, can a structured skill optimization loop — where humans design initial skills and AI refines them based on empirical error analysis — produce skills that show directional improvement over both no-skill baselines and purely AI-generated skills?

### Project Goal

Build a lightweight skill optimization demo that:

1. Tests five prompting conditions (no skill, generic scaffold, self-generated skill, human-curated skill, AI-optimized skill) on an ORQA task subset
2. Uses low-cost models (DeepSeek Chat, OpenRouter free tier)
3. Uses proper dev/test split to validate generalization of optimized skills
4. Produces interpretable results with error analysis
5. Projects how validated skills could be organized as marketplace assets (EvoMap framing)

### Scope of Claims

**What Phase 1 can demonstrate:**
- Whether structured procedural prompting improves LLM reasoning on OR multiple-choice problems
- Whether human-AI collaborative skill refinement produces directional improvement over initial designs
- Whether domain-specific skill content outperforms generic scaffolding of equal length

**What Phase 1 cannot claim:**
- That this generalizes to agentic task execution (Phase 1 is single-turn QA, not multi-step agent tasks)
- That skills are "reliably superior" (sample size supports directional evidence only)
- That marketplace cards represent validated production-ready assets (they are demo metadata showing the schema)

The connection to agent skill optimization and marketplace assets is positioned as **motivation and future direction**, not as a conclusion proven by this demo.

### Why ORQA as Primary Benchmark

| Criterion | ORQA |
|-----------|------|
| **Task format** | Multiple-choice QA — clean input/output, deterministic evaluation |
| **Domain** | Operations research — structured, expert-level reasoning |
| **Skill fit** | OR problems have well-defined solving procedures that map naturally to skills |
| **Evaluation** | Exact match on answer letter — no subjective rubrics |
| **Feasibility** | No Docker/Harbor infrastructure required |

SkillsBench provides important framing context (the curated vs self-generated finding) but is deferred to Phase 2 due to its Docker/Harbor infrastructure requirements.

### What This Project Is NOT

- Not a full SkillsBench reproduction via Harbor
- Not a leaderboard submission
- Not a multi-agent system
- Not a marketplace platform implementation
- Not a statistically powered study — it is a methodology demo with directional evidence

---

## 2. Research Questions

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

---

## 3. Data Strategy

### ORQA Data Source

The ORQA benchmark is published as part of the AAAI 2025 paper: *"Evaluating LLM Reasoning in the Operations Research Domain with ORQA"*.

**Acquisition plan:**
1. Check the paper's official repository / supplementary materials for the dataset
2. If a downloadable dataset exists, extract a representative subset via stratified random sampling
3. If not directly downloadable, curate questions using the fixed inclusion protocol below

**Manual curation protocol (fallback only):**
If the ORQA dataset is not directly downloadable, questions are curated under these fixed rules to prevent cherry-picking:

- **Source priority:** (1) questions reproduced verbatim in the paper, (2) questions from official supplementary materials, (3) questions constructed to match the paper's described problem types and difficulty distribution
- **Inclusion rule:** include ALL questions found in sources (1) and (2) for the target task types, up to the per-split quota. Only use source (3) if (1) + (2) are insufficient.
- **Exclusion rule:** exclude only if a question is ambiguous (multiple defensible answers), requires external data not in the question text, or is a duplicate
- **Ordering:** if more questions are available than needed, select by document order (not researcher preference)
- **Documentation:** record the exact source (page number, table, figure) for every question in `data/orqa/README.md`

### Data Split Design

**Critical methodological requirement:** Data is split into three disjoint sets to prevent train-on-test contamination.

```
Total: ~25 questions per task type (50 total across 2 types)

┌─────────────────────────────────────────────────────┐
│  Seed Set (2-3 per type, ~5 total)                  │
│  Purpose: v0 skill generation examples ONLY         │
│  Never evaluated. Never seen by optimizer.           │
├─────────────────────────────────────────────────────┤
│  Dev Set (5 per type, ~10 total)                    │
│  Purpose: run all 5 conditions, error analysis,     │
│  skill optimization (v1 -> v2)                      │
│  Optimizer sees dev failures to produce v2.          │
├─────────────────────────────────────────────────────┤
│  Test Set (5 per type, ~10 total)                   │
│  Purpose: held-out final evaluation                 │
│  Run all 5 conditions ONCE. Optimizer NEVER sees    │
│  test questions, test failures, or test answers.     │
│  This is the ONLY set used for final comparison.     │
└─────────────────────────────────────────────────────┘
```

**Sampling rule:** If the ORQA dataset is available, questions are selected by stratified random sampling within each task type. The split is fixed before any experiment runs and recorded in `data/orqa/split.json`. No manual cherry-picking of questions.

**Why this split matters:**
- v2_optimized is refined based on dev-set errors. If we evaluate v2 on the same dev set, any improvement could be overfitting to those specific questions.
- By holding out a test set that the optimizer never sees, we can show whether optimization **generalizes** — this is the key research claim.
- Seed examples for v0 generation are fully disjoint from both dev and test, preventing information leakage into the self-generated skill.

### Data Volumes

| Task Type | Seed | Dev | Test | Total |
|-----------|------|-----|------|-------|
| **Linear Programming** | 2-3 | 5 | 5 | 12-13 |
| **Combinatorial Optimization** | 2-3 | 5 | 5 | 12-13 |
| **Total** | ~5 | ~10 | ~10 | ~25 |

**Reporting:**
- Dev results are reported as "development performance" — used to explain the optimization process
- Test results are reported as "held-out evaluation" — the primary evidence for claims
- Both are shown in the report, clearly labeled

### Question Format

Each question is stored as JSON:

```json
{
  "id": "orqa_lp_001",
  "task_type": "linear_programming",
  "split": "dev",
  "question": "A factory produces two products X and Y...",
  "choices": {
    "A": "120",
    "B": "150",
    "C": "180",
    "D": "200"
  },
  "correct_answer": "B",
  "source": "ORQA benchmark, stratified random sample"
}
```

### SkillsBench (Phase 2 — Future Extension)

Deferred to Phase 2. When revisited:
- Extract 3-5 self-contained task definitions from the SkillsBench repo
- Use task descriptions as prompts without Harbor/Docker execution
- Demonstrate that the skill schema generalizes beyond QA to agentic execution

---

## 4. Experimental Design

### Five Conditions

| Condition | Skill Source | Description |
|-----------|-------------|-------------|
| **baseline** | None | Raw LLM, task prompt only with basic CoT |
| **generic_scaffold** | Length-matched generic procedure | A structured prompt with the same format as v1 (steps, checks, verification) but containing **generic problem-solving advice** only — no domain-specific OR content. Controls for the prompt-length/structure confound. |
| **v0_self_generated** | LLM generates from task-type description | LLM receives the task-type description and 2 seed examples (from the disjoint seed set — never from dev or test), then generates a general skill. Two separate LLM calls: (1) generate skill, (2) solve with skill. |
| **v1_curated** | Human-designed | Researcher writes structured skill following the unified schema |
| **v2_optimized** | AI refines v1 based on dev errors | After v1 runs on dev set, dev-set error analysis feeds back into LLM to produce refined skill. **Optimizer never sees test set questions, answers, or failures.** |

**v0 clarification:** The self-generated skill is produced per task type (not per question). The LLM sees 2 seed examples (disjoint from dev and test) to understand the format, but must produce a general-purpose skill.

**generic_scaffold matching rules:** The scaffold must match v1_curated on all structural dimensions to isolate domain content as the only variable:

- **Same YAML schema** — identical fields (name, procedure, common_failures, verification, etc.)
- **Same step count** — if v1 has 6 procedure steps, scaffold has 6 steps
- **Same field density** — each step has a `check`; same number of `common_failures` and `preconditions`
- **Token band** — total scaffold tokens must be within +/- 15% of v1_curated token count
- **Generic content only** — steps describe universal problem-solving (read, identify, plan, execute, verify) with no OR-specific terms, formulas, or domain heuristics

Example (must be adjusted per v1 to match step count and length):
```yaml
procedure:
  - step: "Read the problem carefully and identify what is being asked"
    check: "Can you state the goal in one sentence?"
  - step: "List all given information and constraints"
    check: "Have you captured every number and condition mentioned?"
  - step: "Identify what type of problem this is"
    check: "Can you name the general category?"
  - step: "Choose an appropriate method to solve"
    check: "Does your method match the problem type?"
  - step: "Execute the solution step by step"
    check: "Is each step logically following from the previous?"
  - step: "Verify your answer against all stated constraints"
    check: "Does your answer satisfy every condition in the problem?"
```

**Validation:** Before running experiments, count tokens for both v1_curated and generic_scaffold using the model's tokenizer. Log both counts in results metadata. If they differ by more than 15%, adjust the scaffold.

### Pipeline Flow

```
Phase 0: Data Preparation
  Load questions.json → split into seed / dev / test
  Verify split integrity (no overlap)

Phase 1: Run All Conditions on Dev Set
  For each condition in [baseline, generic_scaffold, v0, v1]:
    agent_runner (dev set) → evaluator → dev results

Phase 2: Error Analysis (Dev Set Only)
  error_analyzer (dev results for all conditions)
  → root cause classification for incorrect answers
  → outcome labels (improved/degraded/no_change) across conditions

Phase 3: Skill Optimization (Using Dev Evidence Only)
  skill_optimizer (v1 skill + dev-set error analysis)
  → produces v2_optimized skill + changelog
  Run v2 on dev set → evaluate (for development tracking only)

Phase 4: Held-Out Test Evaluation
  For each condition in [baseline, generic_scaffold, v0, v1, v2]:
    agent_runner (test set) → evaluator → test results
  This is the primary evidence for all claims.

Phase 5: Report
  report_generator → dev results, test results (clearly separated),
  comparison tables, paired win/loss, case studies, skill diffs
```

### Models

| Model | Source | Config | Role |
|-------|--------|--------|------|
| `deepseek-chat` | DeepSeek API | `temperature: 0`, `max_tokens: 2048` | Primary model for all runs |
| OpenRouter free tier (e.g., `meta-llama/llama-3.1-8b-instruct:free`) | OpenRouter | `temperature: 0`, `max_tokens: 2048` | Secondary cross-model validation (if time allows) |

### Reproducibility Settings

- **Temperature: 0** for all LLM calls — reduces output variance (note: full determinism is not guaranteed on hosted APIs; providers may update models or have residual sampling noise)
- **Fixed model versions** — record exact model identifiers in results
- **All prompts saved** — every LLM call logs the full request and response
- **Run timestamps** — each experiment run gets a unique ID with timestamp
- **Data split frozen** — `split.json` is committed before any runs and never modified

### API Configuration

```yaml
# configs/models.yaml
models:
  deepseek:
    provider: "openai_compatible"
    base_url: "https://api.deepseek.com/v1"
    model: "deepseek-chat"
    api_key_env: "DEEPSEEK_API_KEY"
    temperature: 0
    max_tokens: 2048
    timeout: 60
    retry:
      max_retries: 3
      backoff_seconds: 5

  openrouter_free:
    provider: "openai_compatible"
    base_url: "https://openrouter.ai/api/v1"
    model: "meta-llama/llama-3.1-8b-instruct:free"
    api_key_env: "OPENROUTER_API_KEY"
    temperature: 0
    max_tokens: 2048
    timeout: 60
    retry:
      max_retries: 3
      backoff_seconds: 5
```

**Rate limit handling:** All API calls go through a shared client with:
- Retry on 429/503 with exponential backoff
- 1-second minimum delay between calls (avoid burst rate limits on free tier)
- Graceful failure: if a call fails after 3 retries, log the error and continue with remaining tasks

**Estimated cost:** ~25 questions x 5 conditions x ~2K tokens/call = ~250K tokens total (dev + test). Well within DeepSeek free/cheap tier.

---

## 5. Prompt Templates

### Baseline Prompt (No Skill)

```
You are an expert in operations research. Solve the following multiple-choice problem.

**Problem:**
{question}

**Options:**
A) {choice_a}
B) {choice_b}
C) {choice_c}
D) {choice_d}

Think through this step by step, then provide your final answer.

**IMPORTANT:** Your final line MUST be exactly: "ANSWER: X" where X is A, B, C, or D.
```

### Generic Scaffold Prompt (Length-Matched Control)

```
You are an expert in operations research. You have been given a structured problem-solving guide. Follow the procedure carefully.

**GUIDE:**
{generic_scaffold_yaml}

**Problem:**
{question}

**Options:**
A) {choice_a}
B) {choice_b}
C) {choice_c}
D) {choice_d}

Follow the procedure step by step, then provide your final answer.

**IMPORTANT:** Your final line MUST be exactly: "ANSWER: X" where X is A, B, C, or D.
```

### Skill-Injected Prompt (v0/v1/v2)

```
You are an expert in operations research. You have been given a structured skill to guide your problem-solving approach. Follow the skill's procedure carefully.

**SKILL:**
{skill_yaml}

**Problem:**
{question}

**Options:**
A) {choice_a}
B) {choice_b}
C) {choice_c}
D) {choice_d}

Follow the skill procedure step by step, then provide your final answer.

**IMPORTANT:** Your final line MUST be exactly: "ANSWER: X" where X is A, B, C, or D.
```

### Skill Generation Prompt (for v0_self_generated)

```
You are an expert in operations research and problem-solving methodology.

I need you to create a structured problem-solving skill for the following type of OR problem: {task_type_description}

Here are 2 example problems of this type (for context only — do NOT solve them):
{seed_example_1}
{seed_example_2}

NOTE: These examples are provided only to illustrate the problem format. Your skill must be general-purpose — it should work for ANY problem of this type, not just these examples.

Create a general-purpose skill as a step-by-step procedure with verification checks.

Output the skill in this exact YAML format:

name: [skill name]
version: "v0_self_generated"
source: "self_generated"
domain: "operations_research"
task_type: [task type]
when_to_use: [when this skill applies]
when_not_to_use: [when this skill should NOT be used]
preconditions:
  - [precondition 1]
  - [precondition 2]
procedure:
  - step: [what to do]
    check: [how to verify]
  - step: [what to do]
    check: [how to verify]
common_failures:
  - [failure mode 1]
  - [failure mode 2]
verification: [final check procedure]
```

### Answer Extraction

The evaluator extracts answers using this strategy (in order):
1. **Regex match:** Search for `ANSWER:\s*([A-D])` in the last 5 lines of the response
2. **Fallback regex:** Search for `(?:answer|choice|option)\s*(?:is|:)\s*([A-D])` case-insensitive in the full response
3. **Last letter match:** If response ends with a single capital letter A-D
4. **Failure:** If no answer can be extracted, mark as `extraction_failed`

---

## 6. Skill Schema

All skills follow a unified YAML schema:

```yaml
name: string                    # e.g. "or-linear-programming"
version: string                 # e.g. "v1_curated"
source: enum                    # "self_generated" | "curated" | "optimized"
domain: string                  # e.g. "operations_research"
task_type: string               # e.g. "linear_programming"

when_to_use: string             # Natural language condition
when_not_to_use: string         # Explicit exclusion criteria

preconditions:
  - string                      # What must be true before applying

procedure:
  - step: string                # What to do
    check: string               # How to verify this step is done correctly

common_failures:
  - string                      # Known failure modes to avoid

verification: string            # Final verification procedure

# Metadata (added after evaluation)
evidence:
  benchmark: string
  dev_accuracy: float           # Accuracy on dev set
  test_accuracy: float          # Accuracy on held-out test set
  tasks_tested: int
  error_categories: list
  changelog: string             # What changed from previous version and why
```

### Schema Design Principles

1. **Every step has a check** — skills must be executable, not decorative
2. **common_failures drives optimization** — when we see these failures, we know which part of the skill to strengthen
3. **evidence is attached** — skills carry their own validation data, with dev/test clearly separated
4. **version + source tracks lineage** — can trace from v0 -> v1 -> v2 and know who/what authored each

---

## 7. Classification System

The classification system is split into two independent layers to avoid conflating diagnostics with conclusions.

### Layer 1: Outcome Labels (Automated, Per Question Per Condition)

These are computed mechanically from the evaluation results — no LLM needed.

**Per-condition outcome:**

| Label | Code | How Computed |
|-------|------|-------------|
| Correct | `correct` | Extracted answer matches correct answer |
| Incorrect | `incorrect` | Extracted answer does not match |
| Extraction Failed | `extraction_failed` | Could not parse answer from response |

**Cross-condition outcome** (computed per question, comparing each skill condition to baseline):

| Label | Code | How Computed |
|-------|------|-------------|
| Improved | `improved` | Baseline incorrect, this condition correct |
| Degraded | `degraded` | Baseline correct, this condition incorrect |
| No Change (both correct) | `no_change_correct` | Both baseline and this condition correct |
| No Change (both wrong) | `no_change_incorrect` | Both baseline and this condition incorrect |

### Layer 2: Root Cause Taxonomy (LLM-Assisted, For Incorrect Answers Only)

Applied only to incorrect answers to diagnose **why** the LLM failed. This is the input to the skill optimizer.

| Category | Code | Description |
|----------|------|-------------|
| Task Misunderstood | `task_misunderstood` | LLM misread the problem |
| Constraint Missed | `constraint_missed` | A constraint from the problem was ignored |
| Wrong Reasoning | `wrong_reasoning` | Reasoning steps are logically flawed |
| Calculation Error | `calculation_error` | Math or arithmetic mistake |
| Skill Mismatch | `skill_mismatch` | Skill doesn't fit this task type |
| Skill Overfit | `skill_overfit` | LLM followed skill too rigidly, missed nuance |
| Verbosity Overload | `verbosity_overload` | Skill too long, LLM lost focus |
| Hallucinated Procedure | `hallucinated_procedure` | LLM invented steps not in the skill |

The error analyzer uses the LLM to classify each incorrect answer into one or more root cause categories, with a brief explanation. The LLM receives:
- The original question and correct answer
- The LLM's full response
- The root cause taxonomy as a reference
And outputs a JSON object with `root_causes: [...]` and `explanation: "..."`.

**Separation principle:** Outcome labels go into the report as results. Root causes go into the optimizer as diagnostic input. They are never mixed in the same table or fed to the same consumer.

---

## 8. Skill Optimization Logic

The optimization step is the core research contribution. It works as follows:

### Critical Constraint: Dev-Set Only

The optimizer **only** receives evidence from the dev set. It never sees:
- Test set questions
- Test set answers
- Test set failures or reasoning traces

This ensures that v2's improvement on the test set (if any) represents genuine generalization, not overfitting to specific questions.

### Input to Optimizer

```
1. Current skill (v1_curated)
2. Dev-set tasks where v1 failed (with question text, expected answer, LLM response)
3. Root cause categories for each dev failure (from Layer 2 taxonomy)
4. Full reasoning traces for dev failures
5. Dev-set tasks where v1 succeeded (to avoid breaking what works)
```

### Optimizer Prompt

```
You are a skill optimization expert. You are given:

1. A problem-solving skill that was tested on {n} development tasks
2. It succeeded on {n_success} tasks and failed on {n_fail} tasks
3. Root cause analysis for each failure
4. The full reasoning traces for both successes and failures

**Current Skill:**
{current_skill_yaml}

**Failure Analysis (development set only):**
{dev_failure_details}

**Success Cases (do not break these):**
{dev_success_summaries}

Your job: produce an IMPROVED version of the skill that:
1. Fixes the identified failure patterns
2. Does NOT break the cases that already succeed
3. Stays concise — do not make the skill longer than necessary
4. Produces GENERAL improvements — not fixes targeted at specific questions

Output the complete updated skill in the same YAML format, followed by:

**CHANGELOG:**
- What you changed and why (one bullet per change)
```

### What Can Be Optimized

| Dimension | Example Fix |
|-----------|-------------|
| **Applicability** | Add `when_not_to_use` for task types that cause mismatch |
| **Granularity** | Break a vague step into 2-3 specific sub-steps |
| **Ordering** | Move constraint-checking earlier in the procedure |
| **Constraint coverage** | Add a step for bounds/integer checks if those were missed |
| **Length** | Remove verbose explanations that cause context dilution |
| **Failure avoidance** | Add specific common_failures based on observed error patterns |

---

## 9. Project Structure

```
skill-optimization/
├── README.md                          # Quick start + overview + walkthrough
├── requirements.txt                   # Python dependencies
├── configs/
│   ├── models.yaml                    # Model endpoints and parameters
│   └── experiments.yaml               # Task sets x skill conditions x models
├── src/
│   ├── __init__.py
│   ├── task_loader.py                 # Load tasks, enforce split boundaries
│   ├── skill_manager.py               # Load, version skills from skills/
│   ├── skill_generator.py             # LLM self-generates skill (v0) from seed examples
│   ├── agent_runner.py                # Construct prompts, call LLM, parse answers
│   ├── evaluator.py                   # Score results + compute outcome labels
│   ├── error_analyzer.py              # Root cause classification (Layer 2)
│   ├── skill_optimizer.py             # LLM refines skill (v1 -> v2) using dev evidence only
│   ├── report_generator.py            # Produce markdown reports + comparison tables
│   ├── llm_client.py                  # Shared API client with retry/rate-limit
│   └── run_pipeline.py               # Orchestrate the full pipeline with split enforcement
├── skills/
│   ├── schema.json                    # JSON Schema for skill validation
│   ├── generic_scaffold/              # Length-matched generic control skills
│   └── orqa/
│       ├── v0_self_generated/         # Auto-generated per task type
│       ├── v1_curated/                # Hand-designed
│       └── v2_optimized/              # Refined after dev-set error analysis
├── data/
│   └── orqa/
│       ├── questions.json             # All ~25 questions with split labels
│       ├── split.json                 # Frozen split definition (seed/dev/test IDs)
│       └── README.md                  # Data source, sampling rule, split rationale
├── results/
│   ├── logs/                          # Raw LLM request/response per run
│   ├── evaluations/
│   │   ├── dev/                       # Dev set results (used for optimization)
│   │   └── test/                      # Test set results (held-out, primary evidence)
│   └── analysis/                      # Root cause analysis outputs (dev set only)
└── docs/
    ├── 01_problem_framing.md
    ├── 02_experiment_design.md
    ├── 03_results_and_analysis.md     # Auto-generated by report_generator
    └── 04_marketplace_mapping.md
```

### Dependencies

```
# requirements.txt
python>=3.10
openai>=1.0.0          # OpenAI-compatible API client (works with DeepSeek, OpenRouter)
pyyaml>=6.0            # YAML parsing for skills and configs
jsonschema>=4.0        # Skill schema validation
rich>=13.0             # Terminal output formatting
python-dotenv>=1.0     # Environment variable management
```

---

## 10. Marketplace Mapping (EvoMap Bridge)

**Important framing note:** The marketplace mapping in this demo is a **conceptual projection** — it demonstrates how the skill schema and evidence format could integrate with marketplace platforms like EvoMap. It is NOT validated marketplace evidence. The data volumes and model coverage in Phase 1 are insufficient to make production-ready marketplace claims.

### Asset Type Mapping

| EvoMap Concept | Skill Optimization Equivalent | Example |
|----------------|-------------------------------|---------|
| **Gene** | Atomic skill — single task-type procedure | "LP solver procedure" |
| **Capsule** | Skill + evidence bundle — skill with benchmark validation, error analysis, version history | "LP solver v2 + ORQA results" |
| **Recipe** | Multi-skill workflow — task router + domain-specific skills | "Classify OR problem type -> apply matched skill" |

### Demo Marketplace Card Format

Each validated skill produces a **demo metadata card** (not production marketplace evidence):

```yaml
# NOTE: This is demo metadata showing the schema format.
# Evidence strength is demo-level and requires cross-model,
# larger-sample validation before marketplace publication.

asset_name: "or-linear-programming"
asset_type: "capsule"
domain: "operations_research"
supported_models: ["deepseek-chat"]  # Only validated on this model
evidence:
  benchmark: "ORQA"
  evidence_level: "demo"             # NOT "validated" or "production"
  split: "held-out test set"
  n_test_tasks: 5
  conditions:
    baseline: { test_accuracy: 0.40 }
    generic_scaffold: { test_accuracy: 0.40 }
    v0_self_generated: { test_accuracy: 0.40 }
    v1_curated: { test_accuracy: 0.60 }
    v2_optimized: { test_accuracy: 0.80 }
  key_optimization: "Added constraint verification step; test accuracy +20%"
  dev_vs_test_gap: "Dev: 0.80, Test: 0.80 — no overfitting observed"
version_history:
  - version: "v1_curated"
    author: "human"
    note: "Initial design based on OR textbook problem-solving procedure"
  - version: "v2_optimized"
    author: "deepseek-chat"
    note: "Added integer feasibility check after dev-set failures showed constraint_missed"
quality_signals:
  verification_type: "exact_match"
  dev_test_split: true
  error_analysis: true
  scaffold_controlled: true
  reproducibility: "temperature 0; full determinism not guaranteed on hosted APIs"
```

---

## 11. Success Criteria

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
| Demo marketplace cards are produced | Yes — YAML artifacts with proper caveats |

---

## 12. Scope Boundaries

### In Scope (Phase 1)

- ORQA: ~25 questions, 2 task types, 5 conditions, dev/test split
- DeepSeek Chat as primary model
- One optimization iteration (v1 -> v2) using dev-set evidence only
- Generic scaffold control condition
- Paired win/loss and accuracy delta reporting
- Automated report generation with dev/test results clearly separated
- Marketplace mapping as conceptual projection (with demo-level caveats)

### Out of Scope (Phase 1)

- SkillsBench task execution (deferred to Phase 2)
- Full Harbor/Docker infrastructure
- Multiple optimization iterations (v2 -> v3 -> ...)
- Multi-agent architectures
- Actual EvoMap platform integration
- High-cost model evaluation
- Formal statistical significance testing (sample supports directional evidence only)
- Automated skill routing (manually assign skills to task types)
- Agentic task execution claims (Phase 1 is single-turn QA)

### Phase 2 Extensions (Future Work)

- SkillsBench integration: extract tasks, run with skill injection, validate agent-level claims
- Cross-model comparison (OpenRouter free tier models) for `supported_models` validation
- Multi-round optimization (v2 -> v3 -> v4) with larger dev sets
- Automated task-type routing
- Larger ORQA subsets for statistical power and confidence intervals
- Upgrade marketplace cards from "demo" to "validated" evidence level

---

## 13. Critical Path and Build Order

For a one-day build, this is the implementation sequence. Items marked **(cut if late)** can be dropped without breaking the demo.

| Priority | Module | Depends On | Est. Time |
|----------|--------|-----------|-----------|
| 1 | `llm_client.py` | — | 30 min |
| 2 | `data/orqa/questions.json` + `split.json` | — | 60 min |
| 3 | `task_loader.py` (with split enforcement) | data ready | 20 min |
| 4 | `agent_runner.py` + prompt templates (all 3 types) | llm_client | 45 min |
| 5 | `evaluator.py` + answer extraction + outcome labels | — | 30 min |
| 6 | `run_pipeline.py` (Phase 1: baseline on dev) | 1-5 | 30 min |
| 7 | Write v1_curated skills (2 task types) + generic scaffolds | — | 60 min |
| 8 | `skill_manager.py` | — | 20 min |
| 9 | `skill_generator.py` (v0, using seed examples) | llm_client | 30 min |
| 10 | Run Phase 1: all conditions on dev set | 6-9 | 30 min (API time) |
| 11 | `error_analyzer.py` (root causes, dev only) | llm_client, evaluator | 30 min |
| 12 | `skill_optimizer.py` (dev evidence only) | llm_client | 30 min |
| 13 | Run Phase 3-4: optimize + v2 on dev, all conditions on test | 10-12 | 30 min (API time) |
| 14 | `report_generator.py` (dev/test separated, paired win/loss) | all results | 60 min |
| 15 | README.md with walkthrough | report | 30 min |
| 16 | **(cut if late)** `docs/04_marketplace_mapping.md` | results | 30 min |
| 17 | **(cut if late)** Cross-model run with OpenRouter | all pipeline | 45 min |

**Total estimated: ~10-11 hours** with vibe coding assistance.

**Minimum viable demo (if severely time-constrained):**
Steps 1-13 + a manually written summary = working 5-condition comparison with dev/test results. Everything after step 13 improves the presentation but is not essential to the research claim.

---

## 14. Deliverables

| Deliverable | Format | Purpose |
|-------------|--------|---------|
| Working pipeline | Python scripts in `src/` | Reproducible experiment with split enforcement |
| Skill artifacts | YAML in `skills/` | Versioned skills with dev/test evidence |
| Generic scaffold | YAML in `skills/generic_scaffold/` | Length-matched control condition |
| Raw results | JSON in `results/` (dev/ and test/ separated) | Audit trail |
| Data split | `data/orqa/split.json` | Frozen, auditable split definition |
| Problem framing | `docs/01_problem_framing.md` | Research context with scope-of-claims |
| Experiment design | `docs/02_experiment_design.md` | Methodology with split and control design |
| Results & analysis | `docs/03_results_and_analysis.md` | Auto-generated with dev/test separation |
| Marketplace mapping | `docs/04_marketplace_mapping.md` | Conceptual EvoMap projection (demo-level) |
| README | `README.md` | Quick start + walkthrough narrative |
