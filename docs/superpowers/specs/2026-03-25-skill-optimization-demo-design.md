# Skill Optimization Demo — Design Spec

## 1. Problem Framing

### Background

LLM agents often fail not because of weak general capability, but because they lack stable, reusable procedural knowledge for task completion. A **skill** is an explicit, structured behavioral prior that guides how an agent interprets, decomposes, executes, and verifies a task.

SkillsBench (2025) demonstrated that human-curated skills can improve agent performance, but self-generated skills generally do not help. This raises a critical follow-up question: **can we systematically optimize skills through human-AI collaborative iteration?**

### Core Research Question

Given an agent and a task benchmark, can a structured skill optimization loop — where humans design initial skills and AI refines them based on empirical error analysis — produce skills that reliably outperform both no-skill baselines and purely AI-generated skills?

### Project Goal

Build a lightweight skill optimization demo that:

1. Tests four skill conditions (no skill, self-generated, human-curated, AI-optimized) on an ORQA task subset
2. Uses low-cost models (DeepSeek Chat, OpenRouter free tier)
3. Produces interpretable results with error analysis
4. Maps validated skills to marketplace-ready asset formats (EvoMap framing)

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

---

## 2. Research Questions

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

---

## 3. Data Strategy

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

### SkillsBench (Phase 2 — Future Extension)

Deferred to Phase 2. When revisited:
- Extract 3-5 self-contained task definitions from the SkillsBench repo
- Use task descriptions as prompts without Harbor/Docker execution
- Demonstrate that the skill schema generalizes beyond QA to agentic execution

---

## 4. Experimental Design

### Four Conditions

| Condition | Skill Source | Description |
|-----------|-------------|-------------|
| **baseline** | None | Raw LLM, task prompt only |
| **v0_self_generated** | LLM generates from task-type description | LLM receives the task-type description (e.g., "linear programming problems") and 2 example questions, then generates a general skill. This skill is then used for ALL questions of that type. Two separate LLM calls: (1) generate skill, (2) solve with skill. |
| **v1_curated** | Human-designed | Researcher writes structured skill following the unified schema |
| **v2_optimized** | AI refines v1 based on errors | After v1 runs, error analysis feeds back into LLM to produce refined skill |

**v0 clarification:** The self-generated skill is produced per task type (not per question) to make it comparable to v1_curated. The LLM sees 2 example questions to understand the format, but must produce a general-purpose skill — not a task-specific one.

### Pipeline Flow

```
Phase 1: Baseline
  task_loader → agent_runner (no skill) → evaluator → results

Phase 2: Self-Generated Skill
  task_loader → skill_generator (LLM writes skill per task type) → agent_runner (with v0) → evaluator → results

Phase 3: Curated Skill
  task_loader → skill_manager (load v1) → agent_runner (with v1) → evaluator → results

Phase 4: Error Analysis + Optimization
  error_analyzer (compare all runs, classify failures)
  → skill_optimizer (LLM refines v1 → v2, with error evidence)
  → agent_runner (with v2) → evaluator → results

Phase 5: Report
  report_generator → comparison tables, case studies, skill diffs, marketplace mapping
```

### Models

| Model | Source | Config | Role |
|-------|--------|--------|------|
| `deepseek-chat` | DeepSeek API | `temperature: 0`, `max_tokens: 2048` | Primary model for all runs |
| OpenRouter free tier (e.g., `meta-llama/llama-3.1-8b-instruct:free`) | OpenRouter | `temperature: 0`, `max_tokens: 2048` | Secondary cross-model validation (if time allows) |

### Reproducibility Settings

- **Temperature: 0** for all LLM calls — ensures deterministic outputs
- **Fixed model versions** — record exact model identifiers in results
- **All prompts saved** — every LLM call logs the full request and response
- **Run timestamps** — each experiment run gets a unique ID with timestamp

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

**Estimated cost:** 15 questions x 4 conditions x ~2K tokens/call = ~120K tokens total. Well within DeepSeek free/cheap tier.

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
{skill_schema_template}
```

### Answer Extraction

The evaluator extracts answers using this strategy (in order):
1. **Regex match:** Search for `ANSWER:\s*([A-D])` in the last 5 lines of the response
2. **Fallback regex:** Search for `(?:answer|choice|option)\s*(?:is|:)\s*([A-D])` case-insensitive in the full response
3. **Last letter match:** If response ends with a single capital letter A-D
4. **Failure:** If no answer can be extracted, mark as `extraction_failed` in the error taxonomy

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
  tasks_tested: int
  baseline_accuracy: float
  with_skill_accuracy: float
  error_categories: list
  changelog: string             # What changed from previous version and why
```

### Schema Design Principles

1. **Every step has a check** — skills must be executable, not decorative
2. **common_failures drives optimization** — when we see these failures, we know which part of the skill to strengthen
3. **evidence is attached** — skills carry their own validation data
4. **version + source tracks lineage** — can trace from v0 → v1 → v2 and know who/what authored each

---

## 7. Error Taxonomy

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

The error analyzer uses the LLM to classify each failure into one or more categories, with a brief explanation. The LLM receives:
- The original question and correct answer
- The agent's full response
- The error taxonomy as a reference
And outputs a JSON object with `error_codes: [...]` and `explanation: "..."`.

---

## 8. Skill Optimization Logic

The optimization step is the core research contribution. It works as follows:

### Input to Optimizer

```
1. Current skill (v1_curated)
2. List of tasks where v1 failed (with question text, expected answer, agent response)
3. Error categories for each failure
4. Full reasoning traces for failed tasks
5. List of tasks where v1 succeeded (to avoid breaking what works)
```

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

### What Can Be Optimized

| Dimension | Example Fix |
|-----------|-------------|
| **Applicability** | Add `when_not_to_use` for task types that cause mismatch |
| **Granularity** | Break a vague step into 2-3 specific sub-steps |
| **Ordering** | Move constraint-checking earlier in the procedure |
| **Constraint coverage** | Add a step for bounds/integer checks if those were missed |
| **Length** | Remove verbose explanations that cause context dilution |
| **Failure avoidance** | Add specific common_failures based on observed errors |

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
│   ├── task_loader.py                 # Load tasks from data/
│   ├── skill_manager.py               # Load, version skills from skills/
│   ├── skill_generator.py             # LLM self-generates skill (v0)
│   ├── agent_runner.py                # Construct prompts, call LLM, parse answers
│   ├── evaluator.py                   # Score results (exact match + extraction)
│   ├── error_analyzer.py              # Classify failures using LLM + taxonomy
│   ├── skill_optimizer.py             # LLM refines skill (v1 -> v2)
│   ├── report_generator.py            # Produce markdown reports + comparison tables
│   ├── llm_client.py                  # Shared API client with retry/rate-limit
│   └── run_pipeline.py               # Orchestrate the full pipeline
├── skills/
│   ├── schema.json                    # JSON Schema for skill validation
│   └── orqa/
│       ├── v0_self_generated/         # Auto-generated per task type
│       ├── v1_curated/                # Hand-designed
│       └── v2_optimized/              # Refined after error analysis
├── data/
│   └── orqa/
│       ├── questions.json             # All 15 questions
│       └── README.md                  # Data source and selection rationale
├── results/
│   ├── logs/                          # Raw LLM request/response per run
│   ├── evaluations/                   # Scored results per condition
│   └── analysis/                      # Error analysis outputs
└── docs/
    ├── 01_problem_framing.md
    ├── 02_experiment_design.md
    ├── 03_results_and_analysis.md     # Auto-generated by report_generator
    └── 04_marketplace_mapping.md
```

### Dependencies

```
# requirements.txt
openai>=1.0.0          # OpenAI-compatible API client (works with DeepSeek, OpenRouter)
pyyaml>=6.0            # YAML parsing for skills and configs
jsonschema>=4.0        # Skill schema validation
rich>=13.0             # Terminal output formatting
python-dotenv>=1.0     # Environment variable management
```

---

## 10. Marketplace Mapping (EvoMap Bridge)

After the experiment, validated skills are mapped to EvoMap concepts:

### Asset Type Mapping

| EvoMap Concept | Skill Optimization Equivalent | Example |
|----------------|-------------------------------|---------|
| **Gene** | Atomic skill — single task-type procedure | "LP solver procedure" |
| **Capsule** | Skill + evidence bundle — skill with benchmark validation, error analysis, version history | "LP solver v2 + ORQA results" |
| **Recipe** | Multi-skill workflow — task router + domain-specific skills | "Classify OR problem type -> apply matched skill" |

### Marketplace Card Format

Each validated skill produces a marketplace-ready card:

```yaml
asset_name: "or-linear-programming"
asset_type: "capsule"
domain: "operations_research"
supported_models: ["deepseek-chat"]
evidence:
  benchmark: "ORQA"
  n_tasks: 8
  conditions:
    baseline: { accuracy: 0.45 }
    v0_self_generated: { accuracy: 0.40 }
    v1_curated: { accuracy: 0.70 }
    v2_optimized: { accuracy: 0.80 }
  key_optimization: "Added constraint verification step; accuracy +10%"
version_history:
  - version: "v1_curated"
    author: "human"
    note: "Initial design based on OR textbook problem-solving procedure"
  - version: "v2_optimized"
    author: "deepseek-chat"
    note: "Added integer feasibility check after 3/8 failures were constraint_missed"
quality_signals:
  verification_type: "exact_match"
  error_analysis: true
  reproducible: true
```

---

## 11. Success Criteria

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
| Full process is documented in README | Yes — README walkthrough |

---

## 12. Scope Boundaries

### In Scope (Phase 1)

- ORQA: 15 questions, 2 task types, 4 conditions, full pipeline
- DeepSeek Chat as primary model
- One optimization iteration (v1 -> v2)
- Automated report generation with comparison tables
- Marketplace mapping as conceptual bridge
- README with full walkthrough

### Out of Scope (Phase 1)

- SkillsBench task execution (deferred to Phase 2)
- Full Harbor/Docker infrastructure
- Multiple optimization iterations (v2 -> v3 -> ...)
- Multi-agent architectures
- Actual EvoMap platform integration
- High-cost model evaluation
- Statistical significance testing (sample too small)
- Automated skill routing (manually assign skills to task types)
- Reasoning quality evaluation (focus on accuracy only)

### Phase 2 Extensions (Future Work)

- SkillsBench integration: extract tasks, run with skill injection
- Cross-model comparison (OpenRouter free tier models)
- Multi-round optimization (v2 -> v3 -> v4)
- Automated task-type routing
- Larger ORQA subsets for statistical power

---

## 13. Critical Path and Build Order

For a one-day build, this is the implementation sequence. Items marked **(cut if late)** can be dropped without breaking the demo.

| Priority | Module | Depends On | Est. Time |
|----------|--------|-----------|-----------|
| 1 | `llm_client.py` | — | 30 min |
| 2 | `data/orqa/questions.json` | — | 45 min |
| 3 | `task_loader.py` | data ready | 20 min |
| 4 | `agent_runner.py` + prompt templates | llm_client | 45 min |
| 5 | `evaluator.py` + answer extraction | — | 30 min |
| 6 | `run_pipeline.py` (Phase 1: baseline) | 1-5 | 30 min |
| 7 | Write v1_curated skills (2 task types) | — | 45 min |
| 8 | `skill_manager.py` | — | 20 min |
| 9 | `skill_generator.py` (v0) | llm_client | 30 min |
| 10 | Run Phase 1-3 (baseline + v0 + v1) | 6-9 | 30 min (API time) |
| 11 | `error_analyzer.py` | llm_client, evaluator | 30 min |
| 12 | `skill_optimizer.py` | llm_client | 30 min |
| 13 | Run Phase 4 (optimize + v2 run) | 10-12 | 20 min (API time) |
| 14 | `report_generator.py` | all results | 45 min |
| 15 | README.md with walkthrough | report | 30 min |
| 16 | **(cut if late)** `docs/04_marketplace_mapping.md` | results | 30 min |
| 17 | **(cut if late)** Cross-model run with OpenRouter | all pipeline | 45 min |

**Total estimated: ~8-9 hours** with vibe coding assistance.

**Minimum viable demo (if severely time-constrained):**
Steps 1-10 + a manually written summary = working 4-condition comparison with results table. Everything after step 10 improves the story but is not essential.

---

## 14. Deliverables

| Deliverable | Format | Purpose |
|-------------|--------|---------|
| Working pipeline | Python scripts in `src/` | Reproducible experiment |
| Skill artifacts | YAML in `skills/` | Versioned skills with evidence |
| Raw results | JSON in `results/` | Audit trail |
| Problem framing | `docs/01_problem_framing.md` | Research context |
| Experiment design | `docs/02_experiment_design.md` | Methodology |
| Results & analysis | `docs/03_results_and_analysis.md` | Auto-generated findings |
| Marketplace mapping | `docs/04_marketplace_mapping.md` | EvoMap bridge |
| README | `README.md` | Quick start + walkthrough narrative |
