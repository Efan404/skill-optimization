# Skill Optimization Pipeline — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a complete skill optimization pipeline that runs 5 prompting conditions on ORQA questions with dev/test split, error analysis, skill optimization, and automated reporting.

**Architecture:** Single-loop pipeline orchestrated by `run_pipeline.py`. Each module has one responsibility, communicates via JSON files in `results/`. The pipeline enforces seed/dev/test split boundaries — the optimizer never sees test data.

**Tech Stack:** Python 3.10+, openai SDK (OpenAI-compatible for DeepSeek/OpenRouter), PyYAML, jsonschema, rich, python-dotenv, tiktoken

**Spec:** `docs/superpowers/specs/2026-03-25-skill-optimization-demo-design.md`

---

## File Map

| File | Responsibility |
|------|---------------|
| `requirements.txt` | Python dependencies |
| `.env` | API keys (gitignored) |
| `.env.example` | Template for API keys |
| `.gitignore` | Ignore .env, .venv, __pycache__, results/logs/ |
| `configs/models.yaml` | Model endpoints, params, retry config |
| `configs/experiments.yaml` | Which conditions to run, which splits, which models |
| `data/orqa/questions.json` | All ~25 ORQA questions with split labels |
| `data/orqa/split.json` | Frozen split definition (seed/dev/test IDs) |
| `data/orqa/README.md` | Data source documentation |
| `src/__init__.py` | Package init |
| `src/llm_client.py` | OpenAI-compatible API client with retry, rate-limit, logging |
| `src/task_loader.py` | Load questions, filter by split, validate split integrity, compute dataset label |
| `src/skill_manager.py` | Load/save YAML skills, token counting, scaffold validation |
| `src/skill_generator.py` | LLM generates v0 skill from seed examples |
| `src/agent_runner.py` | Build prompts from templates, call LLM, return raw response |
| `src/evaluator.py` | Extract answers, compute outcome labels (Layer 1) |
| `src/error_analyzer.py` | LLM-assisted root cause classification (Layer 2, dev only, with split assertion) |
| `src/skill_optimizer.py` | LLM refines v1 -> v2 using dev evidence only (with split assertion) |
| `src/report_generator.py` | Produce markdown report with dev/test tables, case studies, marketplace cards |
| `src/run_pipeline.py` | Orchestrate all phases, enforce split boundaries, validate scaffold length |
| `skills/generic_scaffold/generic_problem_solving.yaml` | Length-matched generic control |
| `skills/orqa/v1_curated/linear_programming.yaml` | Hand-designed LP skill |
| `skills/orqa/v1_curated/combinatorial_optimization.yaml` | Hand-designed CO skill |
| `tests/test_evaluator.py` | Tests for answer extraction + outcome labels |
| `tests/test_task_loader.py` | Tests for split enforcement + dataset label |
| `tests/test_skill_manager.py` | Tests for scaffold validation + token counting |
| `README.md` | Quick start + walkthrough |

---

## Task Dependencies

```
Task 1 (scaffolding + llm_client) ──┬──> Task 5 (agent_runner)
                                    ├──> Task 6 (skill_generator)
                                    ├──> Task 7 (error_analyzer)
                                    └──> Task 8 (skill_optimizer)

Task 2 (data + task_loader)   ──────┬──> Task 6 (needs seed examples)
                                    └──> Task 10 (pipeline)

Task 3 (evaluator)            ──────┬──> Task 10 (pipeline)

Task 4 (skill_manager + skills) ────┬──> Task 10 (pipeline)
  (requires tiktoken from Task 1)

Tasks 1-9 ──────────────────────────> Task 10 (pipeline orchestrator)
Task 10 ────────────────────────────> Task 11 (README + integration test)
Task 10 ────────────────────────────> Task 12 (cross-model, optional)
```

**Parallelizable:** Tasks 2, 3, 4 can run in parallel after Task 1 is complete. Tasks 5, 6, 7, 8, 9 can run in parallel after their dependencies are met.

---

### Task 1: Project Scaffolding + LLM Client

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `.gitignore`
- Create: `configs/models.yaml`
- Create: `src/__init__.py`
- Create: `src/llm_client.py`
- Create: `tests/test_llm_client.py`

- [ ] **Step 1: Create `requirements.txt`**

```
openai>=1.0.0
pyyaml>=6.0
jsonschema>=4.0
rich>=13.0
python-dotenv>=1.0
tiktoken>=0.7.0
```

- [ ] **Step 2: Create `.env.example`**

```
DEEPSEEK_API_KEY=your_deepseek_api_key_here
OPENROUTER_API_KEY=your_openrouter_api_key_here
```

- [ ] **Step 3: Create `.gitignore`**

```
.env
.venv/
__pycache__/
*.pyc
results/logs/
.pytest_cache/
```

- [ ] **Step 4: Create `configs/models.yaml`**

```yaml
models:
  deepseek:
    provider: "openai_compatible"
    base_url: "https://api.deepseek.com"
    model: "deepseek-chat"
    api_key_env: "DEEPSEEK_API_KEY"
    temperature: 0
    max_tokens: 2048
    timeout: 60
    retry:
      max_retries: 3
      backoff_seconds: 5
    min_delay_between_calls: 1.0

  openrouter_free:
    provider: "openai_compatible"
    base_url: "https://openrouter.ai/api/v1"
    model: "openai/gpt-oss-120b:free"
    api_key_env: "OPENROUTER_API_KEY"
    temperature: 0
    max_tokens: 2048
    timeout: 120
    retry:
      max_retries: 3
      backoff_seconds: 5
    min_delay_between_calls: 1.0
```

Note: The `openai` Python SDK appends `/v1/chat/completions` to `base_url` automatically, so DeepSeek's base_url should NOT include `/v1`. OpenRouter already includes `/v1` in their documented base URL.

Alternative OpenRouter models to try: `stepfun/step-3.5-flash:free`, `minimax/minimax-m2.5:free`.

- [ ] **Step 5: Create `src/__init__.py`** (empty file)

- [ ] **Step 6: Write `src/llm_client.py`**

Shared LLM client. Must handle:
- Load model config from `configs/models.yaml`
- Load API key from env var specified in config (via python-dotenv)
- OpenAI-compatible `chat.completions.create` call
- Retry on 429/503 with exponential backoff
- Minimum delay between calls (rate limit)
- Log every request/response to `results/logs/{run_id}/` as JSON
- Return structured result: `{"response": str, "model": str, "tokens_used": int, "request_id": str}`

Key interface:
```python
class LLMClient:
    def __init__(self, model_name: str, run_id: str):
        """Load config for model_name from configs/models.yaml.
        Load API key from env var. Create OpenAI client.
        Create log directory results/logs/{run_id}/
        """

    def chat(self, messages: list[dict], purpose: str = "") -> dict:
        """Send messages, retry on failure, log everything.
        purpose: short label for log filenames (e.g. 'baseline_lp_001')
        Returns: {"response": str, "model": str, "tokens_used": int}
        """
```

- [ ] **Step 7: Write `tests/test_llm_client.py`**

Test that config loading works, that missing API key raises clear error, that retry logic is correct (mock the API). Do NOT test actual API calls.

```python
def test_load_config():
    """Config loads correctly from models.yaml"""

def test_missing_api_key_raises():
    """Clear error when env var not set"""

def test_retry_on_429(monkeypatch):
    """Retries with backoff on rate limit"""
```

- [ ] **Step 8: Install deps and run tests**

```bash
cd /Users/efan404/Codes/research/skill-optimization
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install pytest
pytest tests/test_llm_client.py -v
```

- [ ] **Step 9: Commit**

```bash
git add requirements.txt .env.example .gitignore configs/ src/__init__.py src/llm_client.py tests/
git commit -m "feat: add project scaffolding and LLM client with retry/logging"
```

---

### Task 2: ORQA Data + Task Loader

**Depends on:** Task 1 (for installed dependencies)

**Files:**
- Create: `data/orqa/questions.json`
- Create: `data/orqa/split.json`
- Create: `data/orqa/README.md`
- Create: `src/task_loader.py`
- Create: `tests/test_task_loader.py`

- [ ] **Step 1: Research ORQA data availability**

Search for the ORQA dataset from the AAAI 2025 paper: "Evaluating LLM Reasoning in the Operations Research Domain with ORQA". Check:
1. The paper's GitHub repo or supplementary materials
2. The AAAI proceedings page for attached datasets
3. HuggingFace datasets

If dataset is downloadable, use stratified random sampling to select questions. If not, follow the manual curation protocol from the spec: source priority (1) verbatim from paper > (2) supplementary > (3) constructed. Include ALL from (1)/(2) before using (3). Document-order selection, no cherry-picking.

**If data acquisition proves too time-consuming:** Create a well-structured placeholder dataset of ~25 OR questions (clearly labeled as source_category: 3) with realistic difficulty. This unblocks all downstream tasks. Real ORQA data can be swapped in later without code changes.

- [ ] **Step 2: Create `data/orqa/questions.json`**

~25 questions total across 2 task types. Each question format:
```json
{
  "id": "orqa_lp_001",
  "task_type": "linear_programming",
  "split": "seed",
  "question": "A factory produces two products...",
  "choices": {"A": "120", "B": "150", "C": "180", "D": "200"},
  "correct_answer": "B",
  "source_category": 1,
  "source_detail": "ORQA paper, Table 2, Problem 3"
}
```

Split assignment per task type: 2-3 seed, 5 dev, 5 test.

- [ ] **Step 3: Create `data/orqa/split.json`**

```json
{
  "seed": ["orqa_lp_001", "orqa_lp_002", "orqa_co_001", "orqa_co_002"],
  "dev": ["orqa_lp_003", "orqa_lp_004", "orqa_lp_005", "orqa_lp_006", "orqa_lp_007",
           "orqa_co_003", "orqa_co_004", "orqa_co_005", "orqa_co_006", "orqa_co_007"],
  "test": ["orqa_lp_008", "orqa_lp_009", "orqa_lp_010", "orqa_lp_011", "orqa_lp_012",
            "orqa_co_008", "orqa_co_009", "orqa_co_010", "orqa_co_011", "orqa_co_012"]
}
```

- [ ] **Step 4: Create `data/orqa/README.md`**

Document: data source, dataset label ("ORQA subset" or "ORQA-derived evaluation set"), sampling/curation method, per-question source references, split rationale.

- [ ] **Step 5: Write `src/task_loader.py`**

Key interface:
```python
import json
from pathlib import Path

DATA_DIR = Path("data/orqa")

def load_questions(split: str = None) -> list[dict]:
    """Load questions from data/orqa/questions.json.
    If split is specified, filter to only that split.
    Validate against split.json for integrity.
    """

def validate_split_integrity() -> bool:
    """Check: no overlap between seed/dev/test, all IDs accounted for.
    Raises ValueError if integrity check fails.
    """

def get_seed_examples(task_type: str) -> list[dict]:
    """Return seed questions for a specific task type. Used by v0 generator."""

def get_dataset_label() -> str:
    """Inspect all questions' source_category values.
    If ALL are 1 or 2: return 'ORQA subset'
    If ANY are 3: return 'ORQA-derived evaluation set'
    """

def get_questions_by_type(split: str, task_type: str) -> list[dict]:
    """Return questions filtered by both split and task_type."""
```

- [ ] **Step 6: Write `tests/test_task_loader.py`**

```python
def test_load_all_questions():
    """All questions load, have required fields (id, task_type, split, question, choices, correct_answer, source_category)"""

def test_load_by_split():
    """Filtering by split returns correct subset"""

def test_split_integrity():
    """No overlap between seed/dev/test"""

def test_seed_examples_by_type():
    """Returns only seed questions for the given task type"""

def test_dataset_label_all_source_1_2():
    """If all source_category <= 2, label is 'ORQA subset'"""

def test_dataset_label_with_source_3():
    """If any source_category == 3, label is 'ORQA-derived evaluation set'"""
```

- [ ] **Step 7: Run tests**

```bash
pytest tests/test_task_loader.py -v
```

- [ ] **Step 8: Commit**

```bash
git add data/ src/task_loader.py tests/test_task_loader.py
git commit -m "feat: add ORQA data with seed/dev/test split and task loader"
```

---

### Task 3: Evaluator + Answer Extraction

**Depends on:** None (pure logic, no external deps)

**Files:**
- Create: `src/evaluator.py`
- Create: `tests/test_evaluator.py`

- [ ] **Step 1: Write `tests/test_evaluator.py`**

```python
def test_extract_answer_standard():
    """'ANSWER: B' at end of response -> 'B'"""

def test_extract_answer_fallback():
    """'The answer is C' in middle of response -> 'C'"""

def test_extract_answer_last_letter():
    """Response ending with just 'D' -> 'D'"""

def test_extract_answer_failure():
    """No parseable answer -> None"""

def test_evaluate_single_correct():
    """extracted='B', correct='B' -> 'correct'"""

def test_evaluate_single_incorrect():
    """extracted='A', correct='B' -> 'incorrect'"""

def test_evaluate_single_extraction_failed():
    """extracted=None -> 'extraction_failed'"""

def test_compute_outcome_labels_improved():
    """baseline wrong, condition correct -> 'improved'"""

def test_compute_outcome_labels_degraded():
    """baseline correct, condition wrong -> 'degraded'"""

def test_compute_outcome_labels_no_change():
    """both correct -> 'no_change_correct', both wrong -> 'no_change_incorrect'"""
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_evaluator.py -v
```

- [ ] **Step 3: Write `src/evaluator.py`**

Key interface:
```python
import re

def extract_answer(response: str) -> str | None:
    """Extract A/B/C/D from LLM response using 3-tier strategy:
    1. Regex: ANSWER:\s*([A-D]) in last 5 lines
    2. Fallback: (?:answer|choice|option)\s*(?:is|:)\s*([A-D]) case-insensitive
    3. Last letter: response ends with single A-D
    Returns None if extraction fails.
    """

def evaluate_single(extracted: str | None, correct: str) -> str:
    """Returns 'correct', 'incorrect', or 'extraction_failed'"""

def compute_outcome_labels(baseline_results: dict, condition_results: dict) -> dict:
    """Per-question cross-condition labels.
    Returns: {question_id: 'improved'|'degraded'|'no_change_correct'|'no_change_incorrect'}
    """

def evaluate_condition(questions: list[dict], responses: dict[str, str]) -> dict:
    """Evaluate all questions for one condition.
    responses: {question_id: raw_response_string}
    Returns: {question_id: {"extracted": "B", "correct": "B", "outcome": "correct", "response": "..."}}
    """
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_evaluator.py -v
```

- [ ] **Step 5: Commit**

```bash
git add src/evaluator.py tests/test_evaluator.py
git commit -m "feat: add evaluator with answer extraction and outcome labels"
```

---

### Task 4: Skill Manager + Curated Skills + Generic Scaffold

**Depends on:** Task 1 (for tiktoken in requirements.txt)

**Files:**
- Create: `src/skill_manager.py`
- Create: `tests/test_skill_manager.py`
- Create: `skills/schema.json`
- Create: `skills/orqa/v1_curated/linear_programming.yaml`
- Create: `skills/orqa/v1_curated/combinatorial_optimization.yaml`
- Create: `skills/generic_scaffold/generic_problem_solving.yaml`

- [ ] **Step 1: Write `src/skill_manager.py`**

Key interface:
```python
import yaml
import tiktoken
from pathlib import Path

SKILLS_DIR = Path("skills")

def load_skill(path: str) -> dict:
    """Load a YAML skill file, return as dict"""

def save_skill(skill: dict, path: str):
    """Save a skill dict as YAML"""

def skill_to_yaml_string(skill: dict) -> str:
    """Convert skill dict to YAML string (for prompt injection)"""

def get_skill_for_condition(condition: str, task_type: str) -> dict | None:
    """Return the appropriate skill for a condition+task_type.
    - baseline: returns None
    - generic_scaffold: returns skills/generic_scaffold/generic_problem_solving.yaml
    - v0_self_generated: returns skills/orqa/v0_self_generated/{task_type}.yaml
    - v1_curated: returns skills/orqa/v1_curated/{task_type}.yaml
    - v2_optimized: returns skills/orqa/v2_optimized/{task_type}.yaml
    """

def count_skill_tokens(skill: dict, model: str = "gpt-4") -> int:
    """Count tokens in the YAML string representation of a skill.
    Uses tiktoken for token counting.
    """

def validate_scaffold_length(v1_skill: dict, scaffold_skill: dict, tolerance: float = 0.15) -> tuple[bool, dict]:
    """Check scaffold is within +/-15% of v1 token count.
    Returns: (is_valid, {"v1_tokens": N, "scaffold_tokens": M, "ratio": R})
    """
```

- [ ] **Step 2: Write `tests/test_skill_manager.py`**

```python
def test_load_and_save_skill(tmp_path):
    """Round-trip: save then load produces identical dict"""

def test_count_skill_tokens():
    """Token count returns positive integer for a valid skill"""

def test_validate_scaffold_length_pass():
    """Scaffold within 15% of v1 -> True"""

def test_validate_scaffold_length_fail():
    """Scaffold >15% different -> False"""

def test_get_skill_for_baseline():
    """baseline condition returns None"""

def test_get_skill_for_curated():
    """v1_curated returns the correct skill file"""
```

- [ ] **Step 3: Create `skills/schema.json`**

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": ["name", "version", "source", "domain", "task_type", "when_to_use", "procedure", "common_failures", "verification"],
  "properties": {
    "name": {"type": "string"},
    "version": {"type": "string"},
    "source": {"type": "string", "enum": ["self_generated", "curated", "optimized"]},
    "domain": {"type": "string"},
    "task_type": {"type": "string"},
    "when_to_use": {"type": "string"},
    "when_not_to_use": {"type": "string"},
    "preconditions": {"type": "array", "items": {"type": "string"}},
    "procedure": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["step", "check"],
        "properties": {
          "step": {"type": "string"},
          "check": {"type": "string"}
        }
      }
    },
    "common_failures": {"type": "array", "items": {"type": "string"}},
    "verification": {"type": "string"},
    "evidence": {"type": "object"}
  }
}
```

- [ ] **Step 4: Write `skills/orqa/v1_curated/linear_programming.yaml`**

Domain-specific LP skill with 6 procedure steps:
1. **Identify decision variables** — check: "Can you name each variable and state what it represents with units?"
2. **Write the objective function** — check: "Is the objective linear in the decision variables? Is it maximize or minimize?"
3. **List ALL constraints** — check: "Re-read the problem. Have you captured every constraint, including implicit ones?"
4. **Determine variable bounds** — check: "Are non-negativity constraints stated? Any upper bounds or integer requirements?"
5. **Solve** — check: "If 2 variables: use graphical method (find vertices of feasible region, evaluate objective). If more: use algebraic reasoning."
6. **Verify answer** — check: "Substitute your answer back into ALL constraints. Does it satisfy every one? Does it match one of the given options?"

Include 4 common_failures: "Missing a constraint from the problem text", "Confusing maximize with minimize", "Ignoring integer/non-negativity requirements", "Evaluating objective at wrong vertex".

Include 3 preconditions: "Problem has a linear objective function", "Constraints are linear", "Decision variables are identifiable".

- [ ] **Step 5: Write `skills/orqa/v1_curated/combinatorial_optimization.yaml`**

Domain-specific CO skill with 6 procedure steps (matching LP step count):
1. **Identify the combinatorial structure** — check: "What are you choosing from? Permutations, subsets, assignments, or paths?"
2. **Define objective and feasibility** — check: "What makes a solution feasible? What are you optimizing?"
3. **List ALL constraints** — check: "Re-read the problem. Any capacity limits, ordering requirements, or exclusion rules?"
4. **Bound or enumerate the solution space** — check: "How many feasible solutions exist? Can you enumerate them or establish bounds?"
5. **Apply technique** — check: "For small spaces: enumerate all. For structured problems: use greedy/DP. Always justify why your technique works."
6. **Verify** — check: "Does your solution satisfy all constraints? Is there a better feasible solution you missed?"

Include 4 common_failures, 3 preconditions (matching LP density).

- [ ] **Step 6: Write `skills/generic_scaffold/generic_problem_solving.yaml`**

**MUST match v1_curated on ALL structural dimensions:**
- Same YAML schema
- 6 procedure steps (same count as v1)
- 4 common_failures (same count as v1)
- 3 preconditions (same count as v1)
- Token count within +/-15% of v1_curated
- Generic content ONLY — no OR terms, no domain heuristics

```yaml
name: "generic-problem-solving"
version: "v1_scaffold"
source: "curated"
domain: "general"
task_type: "general"
when_to_use: "When solving any structured problem with multiple choice answers"
when_not_to_use: "When the problem requires no reasoning"
preconditions:
  - "Problem statement is clear and complete"
  - "There are well-defined answer options"
  - "The problem has a single correct answer"
procedure:
  - step: "Read the problem carefully and identify exactly what is being asked"
    check: "Can you state the goal in one sentence?"
  - step: "List all given information, numbers, and conditions"
    check: "Have you captured every piece of data mentioned in the problem?"
  - step: "Identify what type of problem this is and what approach to use"
    check: "Can you name the general problem category?"
  - step: "Plan your solution approach before calculating"
    check: "Do you have a clear sequence of steps to follow?"
  - step: "Execute your solution step by step, showing all work"
    check: "Is each step logically following from the previous?"
  - step: "Check your answer against all stated conditions and constraints"
    check: "Does your answer satisfy every requirement in the problem?"
common_failures:
  - "Missing information stated in the problem"
  - "Making calculation errors in intermediate steps"
  - "Not checking the answer against all given conditions"
  - "Rushing to an answer without systematic reasoning"
verification: "Re-read the problem, verify your answer satisfies all stated conditions, and confirm it matches one of the given options"
```

- [ ] **Step 7: Validate scaffold token length**

```python
from src.skill_manager import count_skill_tokens, validate_scaffold_length, load_skill
v1_lp = load_skill("skills/orqa/v1_curated/linear_programming.yaml")
v1_co = load_skill("skills/orqa/v1_curated/combinatorial_optimization.yaml")
scaffold = load_skill("skills/generic_scaffold/generic_problem_solving.yaml")
for name, v1 in [("LP", v1_lp), ("CO", v1_co)]:
    valid, info = validate_scaffold_length(v1, scaffold)
    print(f"{name}: v1={info['v1_tokens']}, scaffold={info['scaffold_tokens']}, ratio={info['ratio']:.2f}, valid={valid}")
    assert valid, f"Scaffold length mismatch for {name}! Adjust scaffold content."
```

If validation fails, adjust the scaffold text length (add or remove detail) until within 15%.

- [ ] **Step 8: Run tests**

```bash
pytest tests/test_skill_manager.py -v
```

- [ ] **Step 9: Commit**

```bash
git add src/skill_manager.py tests/test_skill_manager.py skills/
git commit -m "feat: add skill manager, curated skills, and length-matched scaffold"
```

---

### Task 5: Agent Runner + Prompt Templates

**Depends on:** Task 1 (llm_client)

**Files:**
- Create: `src/agent_runner.py`

- [ ] **Step 1: Write `src/agent_runner.py`**

Key interface:
```python
from src.llm_client import LLMClient
from src.skill_manager import skill_to_yaml_string

BASELINE_PROMPT = """You are an expert in operations research. Solve the following multiple-choice problem.

**Problem:**
{question}

**Options:**
A) {choice_a}
B) {choice_b}
C) {choice_c}
D) {choice_d}

Think through this step by step, then provide your final answer.

**IMPORTANT:** Your final line MUST be exactly: "ANSWER: X" where X is A, B, C, or D."""

SCAFFOLD_PROMPT = """You are an expert in operations research. You have been given a structured problem-solving guide. Follow the procedure carefully.

**GUIDE:**
{scaffold_yaml}

**Problem:**
{question}

**Options:**
A) {choice_a}
B) {choice_b}
C) {choice_c}
D) {choice_d}

Follow the procedure step by step, then provide your final answer.

**IMPORTANT:** Your final line MUST be exactly: "ANSWER: X" where X is A, B, C, or D."""

SKILL_PROMPT = """You are an expert in operations research. You have been given a structured skill to guide your problem-solving approach. Follow the skill's procedure carefully.

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

**IMPORTANT:** Your final line MUST be exactly: "ANSWER: X" where X is A, B, C, or D."""


def build_prompt(question: dict, condition: str, skill: dict | None = None) -> list[dict]:
    """Build chat messages for a given condition.
    - baseline: uses BASELINE_PROMPT
    - generic_scaffold: uses SCAFFOLD_PROMPT + scaffold YAML
    - v0_self_generated/v1_curated/v2_optimized: uses SKILL_PROMPT + skill YAML
    Returns list of message dicts [{"role": "user", "content": "..."}]
    """

def run_single(client: LLMClient, question: dict, condition: str, skill: dict | None = None) -> dict:
    """Run a single question under a single condition.
    Returns: {"question_id": str, "condition": str, "response": str, "model": str, "tokens_used": int}
    """

def run_condition(client: LLMClient, questions: list[dict], condition: str, skill: dict | None = None) -> dict:
    """Run all questions for a single condition.
    Returns: {question_id: run_single_result}
    """
```

- [ ] **Step 2: Commit**

```bash
git add src/agent_runner.py
git commit -m "feat: add agent runner with prompt templates for all 5 conditions"
```

---

### Task 6: Skill Generator (v0 Self-Generated)

**Depends on:** Task 1 (llm_client), Task 2 (task_loader for seed examples)

**Files:**
- Create: `src/skill_generator.py`

- [ ] **Step 1: Write `src/skill_generator.py`**

Key interface:
```python
from src.llm_client import LLMClient
from src.skill_manager import save_skill
from src.task_loader import get_seed_examples

SKILL_GEN_PROMPT = """You are an expert in operations research and problem-solving methodology.

I need you to create a structured problem-solving skill for the following type of OR problem: {task_type_description}

Here are 2 example problems of this type (for context only — do NOT solve them):

Example 1:
{seed_example_1}

Example 2:
{seed_example_2}

NOTE: These examples are provided only to illustrate the problem format. Your skill must be general-purpose — it should work for ANY problem of this type, not just these examples.

Create a general-purpose skill as a step-by-step procedure with verification checks.

Output the skill in this exact YAML format:

name: [skill name]
version: "v0_self_generated"
source: "self_generated"
domain: "operations_research"
task_type: {task_type}
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
verification: [final check procedure]"""

TASK_TYPE_DESCRIPTIONS = {
    "linear_programming": "Linear programming problems where you must optimize a linear objective function subject to linear constraints",
    "combinatorial_optimization": "Combinatorial optimization problems involving discrete choices, assignments, scheduling, or counting"
}

def extract_yaml_from_response(response: str) -> str:
    """Extract YAML content from LLM response.
    Try: code block (```yaml ... ```) first, then raw YAML detection.
    """

def generate_skill(client: LLMClient, task_type: str, seed_examples: list[dict]) -> dict:
    """Use LLM to generate a v0 skill for a task type.
    - Uses SKILL_GEN_PROMPT with seed examples (disjoint from dev/test)
    - Parses YAML output from LLM response
    - Saves to skills/orqa/v0_self_generated/{task_type}.yaml
    - Returns the parsed skill dict
    """
```

- [ ] **Step 2: Commit**

```bash
git add src/skill_generator.py
git commit -m "feat: add v0 skill generator using seed examples"
```

---

### Task 7: Error Analyzer (Layer 2 Root Causes)

**Depends on:** Task 1 (llm_client)

**Files:**
- Create: `src/error_analyzer.py`

- [ ] **Step 1: Write `src/error_analyzer.py`**

Key interface:
```python
from src.llm_client import LLMClient

ROOT_CAUSE_CODES = [
    "task_misunderstood", "constraint_missed", "wrong_reasoning",
    "calculation_error", "skill_mismatch", "skill_overfit",
    "verbosity_overload", "hallucinated_procedure"
]

ERROR_ANALYSIS_PROMPT = """You are an expert at diagnosing reasoning failures in LLM outputs.

Given a question, the correct answer, and the LLM's response, classify WHY the LLM got it wrong.

**Question:** {question}
**Correct Answer:** {correct_answer}
**LLM's Response:** {response}
**Condition:** {condition} (the prompting strategy used)

Classify the failure into one or more of these root cause categories:
- task_misunderstood: LLM misread the problem
- constraint_missed: A constraint from the problem was ignored
- wrong_reasoning: Reasoning steps are logically flawed
- calculation_error: Math or arithmetic mistake
- skill_mismatch: Skill doesn't fit this task type
- skill_overfit: LLM followed skill too rigidly, missed nuance
- verbosity_overload: Skill too long, LLM lost focus
- hallucinated_procedure: LLM invented steps not in the skill

Respond with ONLY valid JSON (no markdown, no explanation outside JSON):
{{"root_causes": ["category1", "category2"], "explanation": "Brief explanation of what went wrong"}}"""


def analyze_single_failure(
    client: LLMClient,
    question: dict,
    response: str,
    condition: str
) -> dict:
    """Use LLM to classify why a specific answer was wrong.
    ASSERTION: question["split"] must be "dev". Raises ValueError if not.
    Returns: {"root_causes": ["constraint_missed", ...], "explanation": "..."}
    """

def analyze_dev_failures(
    client: LLMClient,
    dev_questions: list[dict],
    dev_results: dict,
) -> dict:
    """Analyze all incorrect answers on the dev set.
    ASSERTION: all questions must have split=="dev". Raises ValueError if any test question found.
    Saves analysis to results/analysis/dev_error_analysis.json.
    Returns: {condition: {question_id: {"root_causes": [...], "explanation": "..."}}}
    """
```

- [ ] **Step 2: Commit**

```bash
git add src/error_analyzer.py
git commit -m "feat: add error analyzer with split assertion and root cause classification"
```

---

### Task 8: Skill Optimizer (v1 -> v2)

**Depends on:** Task 1 (llm_client)

**Files:**
- Create: `src/skill_optimizer.py`

- [ ] **Step 1: Write `src/skill_optimizer.py`**

Key interface:
```python
from src.llm_client import LLMClient
from src.skill_manager import save_skill
from src.skill_generator import extract_yaml_from_response

OPTIMIZER_PROMPT = """You are a skill optimization expert. You are given:

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
- What you changed and why (one bullet per change)"""


def optimize_skill(
    client: LLMClient,
    current_skill: dict,
    dev_failures: list[dict],
    dev_successes: list[dict],
    task_type: str
) -> tuple[dict, str]:
    """Use LLM to refine a v1 skill based on dev-set error analysis.
    ASSERTION: all failure/success items must come from dev split. Validates by checking
    that each item's question has split=="dev". Raises ValueError if test data detected.
    - Parses YAML skill + changelog from LLM output
    - Saves to skills/orqa/v2_optimized/{task_type}.yaml
    - Returns: (optimized_skill_dict, changelog_string)
    """
```

- [ ] **Step 2: Commit**

```bash
git add src/skill_optimizer.py
git commit -m "feat: add skill optimizer with dev-only assertion and changelog extraction"
```

---

### Task 9: Report Generator

**Depends on:** None (pure formatting)

**Files:**
- Create: `src/report_generator.py`

- [ ] **Step 1: Write `src/report_generator.py`**

Key interface:
```python
from pathlib import Path
import yaml

def compute_accuracy(results: dict, questions: list[dict], task_type: str = None) -> float:
    """Compute accuracy for a set of results, optionally filtered by task_type."""

def compute_paired_win_loss(baseline_results: dict, condition_results: dict) -> dict:
    """Returns: {"wins": N, "losses": N, "ties_correct": N, "ties_incorrect": N, "net_delta": N}"""

def generate_report(
    dev_results: dict,
    test_results: dict,
    dev_analysis: dict,
    skills: dict,
    changelogs: dict,
    dataset_label: str,
    run_id: str,
    model_name: str,
    questions: list[dict],
) -> str:
    """Generate full markdown report. Saves to docs/03_results_and_analysis.md.

    Report sections:
    1. Overview — run_id, timestamp, model, dataset_label, question counts
    2. Dev Accuracy Summary — 5 conditions x 2 task types + overall
    3. Dev Root Cause Distribution — table of root cause counts per condition
    4. Test Accuracy Summary (PRIMARY EVIDENCE) — 5 conditions x 2 task types + overall
    5. Paired Win/Loss (test set) — each condition vs baseline, v2 vs v1
       Format:
       | Condition vs Baseline | Wins | Losses | Ties (correct) | Ties (wrong) | Net |
       |---|---|---|---|---|---|
    6. Dev-to-Test Gap — descriptive signal, not pass/fail
       | Condition | Dev Acc | Test Acc | Gap |
    7. Hypothesis Check — state expected vs observed, directional assessment
    8. Per-Question Test Results
       | QID | Type | Baseline | Scaffold | v0 | v1 | v2 | Correct |
    9. Skill Optimization Diff — v1->v2 changelogs
    10. Case Studies — pick 3 success + 3 failure from test results
    """

def generate_marketplace_cards(
    test_results: dict,
    dev_results: dict,
    skills: dict,
    changelogs: dict,
    dataset_label: str,
    model_name: str,
    questions: list[dict],
) -> None:
    """Generate demo marketplace cards.
    Save to results/marketplace_cards/{task_type}.yaml
    Card format follows spec Section 10 with evidence_level: "demo"
    and explicit limitations list.
    """
```

- [ ] **Step 2: Commit**

```bash
git add src/report_generator.py
git commit -m "feat: add report generator with dev/test separation and marketplace cards"
```

---

### Task 10: Pipeline Orchestrator

**Depends on:** ALL previous tasks (1-9)

**Files:**
- Create: `src/run_pipeline.py`
- Create: `configs/experiments.yaml`

- [ ] **Step 1: Create `configs/experiments.yaml`**

```yaml
experiment:
  name: "skill-optimization-v1"
  model: "deepseek"
  conditions:
    - "baseline"
    - "generic_scaffold"
    - "v0_self_generated"
    - "v1_curated"
    - "v2_optimized"
  task_types:
    - "linear_programming"
    - "combinatorial_optimization"
```

- [ ] **Step 2: Write `src/run_pipeline.py`**

Main entry point. Orchestrates all phases with strict split enforcement.

```python
import argparse
import json
from datetime import datetime
from pathlib import Path
from rich.console import Console

from src.llm_client import LLMClient
from src.task_loader import load_questions, validate_split_integrity, get_seed_examples, get_dataset_label, get_questions_by_type
from src.skill_manager import get_skill_for_condition, validate_scaffold_length, load_skill
from src.skill_generator import generate_skill
from src.agent_runner import run_condition
from src.evaluator import evaluate_condition, compute_outcome_labels
from src.error_analyzer import analyze_dev_failures
from src.skill_optimizer import optimize_skill
from src.report_generator import generate_report, generate_marketplace_cards

def run_pipeline(model_name: str = "deepseek", run_id: str = None):
    """
    Phase 0: Validate data + scaffold
      - validate_split_integrity()
      - validate_scaffold_length() for each v1 skill vs generic scaffold
      - compute dataset_label via get_dataset_label()

    Phase 1: Run baseline, generic_scaffold, v0, v1 on DEV set
      - Generate v0 skills using seed examples (get_seed_examples)
      - Run all 4 conditions on dev questions
      - Evaluate all dev results

    Phase 2: Error Analysis (DEV ONLY)
      - analyze_dev_failures() — root causes for all incorrect dev answers
      - Save to results/analysis/

    Phase 3: Optimize v1 -> v2 (DEV evidence ONLY)
      - optimize_skill() for each task type
      - Run v2 on dev set (for tracking only)
      - Evaluate v2 dev results

    Phase 4: Run ALL 5 conditions on TEST set (HELD OUT)
      - This is the ONLY phase that touches test data
      - Run once, evaluate, save to results/evaluations/test/

    Phase 5: Generate report + marketplace cards
      - generate_report() with dev/test clearly separated
      - generate_marketplace_cards()
      - Save report to docs/03_results_and_analysis.md
    """

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="deepseek")
    parser.add_argument("--run-id", default=None)
    args = parser.parse_args()
    run_pipeline(model_name=args.model, run_id=args.run_id)
```

- [ ] **Step 3: Commit**

```bash
git add src/run_pipeline.py configs/experiments.yaml
git commit -m "feat: add pipeline orchestrator with split and scaffold enforcement"
```

---

### Task 11: README + Integration Test

**Depends on:** Task 10

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write `README.md`**

Structure:
1. **Skill Optimization Demo** — one-line description
2. **Quick Start** — clone, `pip install`, set `.env`, `python -m src.run_pipeline --model deepseek`
3. **What This Does** — 5 conditions, dev/test split, optimization loop, report generation
4. **Project Structure** — file tree from spec Section 9
5. **Methodology** — dev/test split, scaffold control, scope of claims
6. **Results** — pointer to `docs/03_results_and_analysis.md`
7. **Limitations** — demo-level evidence, single model, small sample

- [ ] **Step 2: Run full pipeline end-to-end**

```bash
source .venv/bin/activate
python -m src.run_pipeline --model deepseek
```

Verify:
- Phase 0 passes (split integrity + scaffold length validation)
- All 5 conditions produce results for dev and test
- v0 skills are generated and saved to `skills/orqa/v0_self_generated/`
- v2 skills are optimized and saved to `skills/orqa/v2_optimized/` with changelogs
- Error analysis saved to `results/analysis/`
- Report generated at `docs/03_results_and_analysis.md`
- Marketplace cards generated at `results/marketplace_cards/`
- No test data appears in optimizer logs or error analysis

- [ ] **Step 3: Run all tests**

```bash
pytest tests/ -v
```

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "feat: add README with walkthrough and methodology notes"
```

---

### Task 12 (cut if late): Cross-Model Validation

**Depends on:** Task 10

**Files:**
- No new files — uses existing pipeline with `--model openrouter_free`

- [ ] **Step 1: Run pipeline with OpenRouter free model**

```bash
python -m src.run_pipeline --model openrouter_free
```

If `openai/gpt-oss-120b:free` has issues, try `stepfun/step-3.5-flash:free` or `minimax/minimax-m2.5:free` by editing `configs/models.yaml`.

- [ ] **Step 2: Update report to include cross-model comparison**

Manually add a section to the report or extend `report_generator.py` to accept multiple model results.

- [ ] **Step 3: Commit**

```bash
git add .
git commit -m "feat: add cross-model validation with OpenRouter free tier"
```
