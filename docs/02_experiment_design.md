# Experiment Design: Skill Optimization Pipeline

## Data Strategy

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

**Dataset labeling rule:**
- If all questions come from source (1) or (2): label the dataset as **"ORQA subset"** in all reporting
- If any questions come from source (3): label the dataset as **"ORQA-derived evaluation set"** in all reporting, and note the proportion of constructed questions

This label propagates to results, marketplace cards, and all documentation. The `questions.json` file records each question's source category.

### Data Split Design

**Critical methodological requirement:** Data is split into three disjoint sets to prevent train-on-test contamination.

```
Total: ~25 questions (across 2 task types)

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

**Sampling rule:** If the ORQA dataset is available, questions are selected by stratified random sampling within each task type. The split is fixed before any experiment runs and recorded in `data/orqa/split.json`. No manual cherry-picking.

**Why this split matters:**
- v2_optimized is refined based on dev-set errors. If we evaluate v2 on the same dev set, improvement could be overfitting.
- The held-out test set that the optimizer never sees validates whether optimization **generalizes**.
- Seed examples for v0 generation are fully disjoint from both dev and test, preventing information leakage.

### Data Volumes

| Task Type | Seed | Dev | Test | Total |
|-----------|------|-----|------|-------|
| **Linear Programming** | 2-3 | 5 | 5 | 12-13 |
| **Combinatorial Optimization** | 2-3 | 5 | 5 | 12-13 |
| **Total** | ~5 | ~10 | ~10 | ~25 |

### Reporting

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
  "source_category": 1,
  "source_detail": "ORQA paper, Table 2, Problem 3"
}
```

## Five Experimental Conditions

| Condition | Skill Source | Description |
|-----------|-------------|-------------|
| **baseline** | None | Raw LLM, task prompt only with basic CoT |
| **generic_scaffold** | Length-matched generic procedure | A structured prompt with the same format as v1 (steps, checks, verification) but containing **generic problem-solving advice** only — no domain-specific OR content. Controls for the prompt-length/structure confound. |
| **v0_self_generated** | LLM generates from task-type description | LLM receives the task-type description and 2 seed examples (from the disjoint seed set — never from dev or test), then generates a general skill. Two separate LLM calls: (1) generate skill, (2) solve with skill. |
| **v1_curated** | Human-designed | Researcher writes structured skill following the unified schema |
| **v2_optimized** | AI refines v1 based on dev errors | After v1 runs on dev set, dev-set error analysis feeds into LLM to produce refined skill. **Optimizer never sees test set.** |

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

## Pipeline Flow

```
Phase 0: Data Preparation
  Load questions.json -> split into seed / dev / test
  Verify split integrity (no overlap)

Phase 1: Run All Conditions on Dev Set
  For each condition in [baseline, generic_scaffold, v0, v1]:
    agent_runner (dev set) -> evaluator -> dev results

Phase 2: Error Analysis (Dev Set Only)
  error_analyzer (dev results for all conditions)
  -> root cause classification for incorrect answers
  -> outcome labels (improved/degraded/no_change) across conditions

Phase 3: Skill Optimization (Using Dev Evidence Only)
  skill_optimizer (v1 skill + dev-set error analysis)
  -> produces v2_optimized skill + changelog
  Run v2 on dev set -> evaluate (for development tracking only)

Phase 4: Held-Out Test Evaluation
  For each condition in [baseline, generic_scaffold, v0, v1, v2]:
    agent_runner (test set) -> evaluator -> test results
  This is the primary evidence for all claims.

Phase 5: Report
  report_generator -> dev results, test results (clearly separated),
  comparison tables, paired win/loss, case studies, skill diffs
```

## Models

| Model | Source | Config | Role |
|-------|--------|--------|------|
| `deepseek-chat` | DeepSeek API | `temperature: 0`, `max_tokens: 2048` | Primary model for all runs |
| OpenRouter free tier | OpenRouter | `temperature: 0`, `max_tokens: 2048` | Secondary cross-model validation (if time allows) |

## Reproducibility Settings

- **Temperature: 0** for all LLM calls — reduces output variance (note: full determinism is not guaranteed on hosted APIs; providers may update models or have residual sampling noise)
- **Fixed model versions** — record exact model identifiers in results
- **All prompts saved** — every LLM call logs the full request and response
- **Run timestamps** — each experiment run gets a unique ID with timestamp
- **Data split frozen** — `split.json` is committed before any runs and never modified

## API Configuration

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

**Rate limit handling:**
- Retry on 429/503 with exponential backoff
- 1-second minimum delay between calls
- Graceful failure: if a call fails after 3 retries, log the error and continue

**Estimated cost:** ~25 questions x 5 conditions x ~2K tokens/call = ~250K tokens total. Well within DeepSeek free/cheap tier.

## Prompt Templates

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

### Answer Extraction Strategy

The evaluator extracts answers using this strategy (in priority order):
1. **Regex match:** Search for `ANSWER:\s*([A-D])` in the last 5 lines of the response
2. **Fallback regex:** Search for `(?:answer|choice|option)\s*(?:is|:)\s*([A-D])` case-insensitive in the full response
3. **Last letter match:** If response ends with a single capital letter A-D
4. **Failure:** If no answer can be extracted, mark as `extraction_failed`

## Classification System

The classification system is split into two independent layers to avoid conflating diagnostics with conclusions.

### Layer 1: Outcome Labels (Automated)

Computed mechanically from evaluation results — no LLM needed.

**Per-condition outcome:**

| Label | Code | How Computed |
|-------|------|-------------|
| Correct | `correct` | Extracted answer matches correct answer |
| Incorrect | `incorrect` | Extracted answer does not match |
| Extraction Failed | `extraction_failed` | Could not parse answer from response |

**Cross-condition outcome** (per question, comparing each skill condition to baseline):

| Label | Code | How Computed |
|-------|------|-------------|
| Improved | `improved` | Baseline incorrect, this condition correct |
| Degraded | `degraded` | Baseline correct, this condition incorrect |
| No Change (both correct) | `no_change_correct` | Both correct |
| No Change (both wrong) | `no_change_incorrect` | Both incorrect |

### Layer 2: Root Cause Taxonomy (LLM-Assisted, Incorrect Answers Only)

Applied only to incorrect answers to diagnose **why** the LLM failed. This is the input to the skill optimizer (dev set only).

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

**Separation principle:** Outcome labels go into the report as results. Root causes go into the optimizer as diagnostic input. They are never mixed in the same table.

## Skill Optimization Logic

### Critical Constraint: Dev-Set Only

The optimizer **only** receives evidence from the dev set. It never sees:
- Test set questions
- Test set answers
- Test set failures or reasoning traces

This ensures that v2's improvement on the test set (if any) represents genuine generalization.

### Input to Optimizer

1. Current skill (v1_curated)
2. Dev-set tasks where v1 failed (with question text, expected answer, LLM response)
3. Root cause categories for each dev failure
4. Full reasoning traces for dev failures
5. Dev-set tasks where v1 succeeded (to avoid breaking what works)

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

### Optimization Dimensions

| Dimension | Example Fix |
|-----------|-------------|
| **Applicability** | Add `when_not_to_use` for task types that cause mismatch |
| **Granularity** | Break a vague step into 2-3 specific sub-steps |
| **Ordering** | Move constraint-checking earlier in the procedure |
| **Constraint coverage** | Add a step for bounds/integer checks if those were missed |
| **Length** | Remove verbose explanations that cause context dilution |
| **Failure avoidance** | Add specific common_failures based on observed error patterns |
