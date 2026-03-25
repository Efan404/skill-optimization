# Experiment Design: Skill Optimization Pipeline

## Data Strategy

### ORQA Data Source

The ORQA benchmark is published as part of the AAAI 2025 paper: *"Evaluating LLM Reasoning in the Operations Research Domain with ORQA"*.

**Acquisition plan:**
1. Check the paper's official repository / supplementary materials for the dataset
2. If a downloadable dataset exists, extract a representative subset
3. If not directly downloadable, manually curate 15 questions from the paper's examples and described problem types

**Target subset: 15 questions** covering two primary OR task types:

| Task Type | Target Count | Why |
|-----------|-------------|-----|
| **Linear Programming** | 7-8 | Classic OR, well-structured, clear skill mapping |
| **Combinatorial Optimization** | 7-8 | More complex reasoning, tests skill limits |

**Why 15 questions and 2 task types:**
- 15 questions x 4 conditions = 60 data points — enough to show patterns
- 2 task types allow cross-type comparison without exploding the skill curation workload
- Each task type gets its own skill through all 4 conditions = 8 skill variants total (manageable)

### Question Format

Each question is stored as JSON:

```json
{
  "id": "orqa_lp_001",
  "task_type": "linear_programming",
  "question": "A factory produces two products X and Y...",
  "choices": {
    "A": "120",
    "B": "150",
    "C": "180",
    "D": "200"
  },
  "correct_answer": "B",
  "source": "ORQA benchmark, adapted from Problem 3.2"
}
```

## Four Experimental Conditions

| Condition | Skill Source | Description |
|-----------|-------------|-------------|
| **baseline** | None | Raw LLM, task prompt only |
| **v0_self_generated** | LLM generates from task-type description | LLM receives the task-type description and 2 example questions, then generates a general skill. This skill is then used for ALL questions of that type. Two separate LLM calls: (1) generate skill, (2) solve with skill. |
| **v1_curated** | Human-designed | Researcher writes structured skill following the unified schema |
| **v2_optimized** | AI refines v1 based on errors | After v1 runs, error analysis feeds back into LLM to produce refined skill |

**v0 clarification:** The self-generated skill is produced per task type (not per question) to make it comparable to v1_curated. The LLM sees 2 example questions to understand the format, but must produce a general-purpose skill — not a task-specific one.

## Pipeline Flow

```
Phase 1: Baseline
  task_loader -> agent_runner (no skill) -> evaluator -> results

Phase 2: Self-Generated Skill
  task_loader -> skill_generator (LLM writes skill per task type)
             -> agent_runner (with v0) -> evaluator -> results

Phase 3: Curated Skill
  task_loader -> skill_manager (load v1)
             -> agent_runner (with v1) -> evaluator -> results

Phase 4: Error Analysis + Optimization
  error_analyzer (compare all runs, classify failures)
  -> skill_optimizer (LLM refines v1 -> v2, with error evidence)
  -> agent_runner (with v2) -> evaluator -> results

Phase 5: Report
  report_generator -> comparison tables, case studies, skill diffs, marketplace mapping
```

## Models

| Model | Source | Config | Role |
|-------|--------|--------|------|
| `deepseek-chat` | DeepSeek API | `temperature: 0`, `max_tokens: 2048` | Primary model for all runs |
| OpenRouter free tier | OpenRouter | `temperature: 0`, `max_tokens: 2048` | Secondary cross-model validation (if time allows) |

## Reproducibility Settings

- **Temperature: 0** for all LLM calls — ensures deterministic outputs
- **Fixed model versions** — record exact model identifiers in results
- **All prompts saved** — every LLM call logs the full request and response
- **Run timestamps** — each experiment run gets a unique ID with timestamp

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

**Estimated cost:** 15 questions x 4 conditions x ~2K tokens/call = ~120K tokens total. Well within DeepSeek free/cheap tier.

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
{example_1}
{example_2}

Create a general-purpose skill that would help someone systematically solve ANY problem of this type. The skill should be a step-by-step procedure with verification checks.

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

## Error Taxonomy

Predefined error categories for failure classification:

| Category | Code | Description |
|----------|------|-------------|
| Task Misunderstood | `task_misunderstood` | Agent misread the problem |
| Constraint Missed | `constraint_missed` | A constraint from the problem was ignored |
| Wrong Reasoning | `wrong_reasoning` | Reasoning steps are logically flawed |
| Calculation Error | `calculation_error` | Math or arithmetic mistake |
| Skill Mismatch | `skill_mismatch` | Skill doesn't fit this task type |
| Skill Overfit | `skill_overfit` | Agent followed skill too rigidly, missed nuance |
| Verbosity Overload | `verbosity_overload` | Skill too long, agent lost focus |
| Hallucinated Procedure | `hallucinated_procedure` | Agent invented steps not in the skill |
| Answer Extraction Failed | `extraction_failed` | Could not parse a valid answer from response |
| Correct Without Skill | `correct_baseline` | Baseline correct — skill not needed |
| Improved With Skill | `improved_with_skill` | Skill helped |
| Degraded With Skill | `degraded_with_skill` | Skill hurt performance |

The error analyzer uses the LLM to classify each failure into one or more categories, with a brief explanation.

## Skill Optimization Logic

### Input to Optimizer

1. Current skill (v1_curated)
2. List of tasks where v1 failed (with question text, expected answer, agent response)
3. Error categories for each failure
4. Full reasoning traces for failed tasks
5. List of tasks where v1 succeeded (to avoid breaking what works)

### Optimizer Prompt

```
You are a skill optimization expert. You are given:

1. A problem-solving skill that was tested on {n} benchmark tasks
2. It succeeded on {n_success} tasks and failed on {n_fail} tasks
3. Error analysis for each failure (error categories + explanations)
4. The full reasoning traces for both successes and failures

**Current Skill:**
{current_skill_yaml}

**Failure Analysis:**
{failure_details}

**Success Cases (do not break these):**
{success_summaries}

Your job: produce an IMPROVED version of the skill that:
1. Fixes the identified failure patterns
2. Does NOT break the cases that already succeed
3. Stays concise — do not make the skill longer than necessary

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
| **Failure avoidance** | Add specific common_failures based on observed errors |
