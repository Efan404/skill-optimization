# ORQA Track A Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add an independent ORQA Track A runner that evaluates `baseline`, `generic_scaffold`, `v1_curated`, `v1_component_minimal`, and `v1_component_enriched` with the existing ORQA pipeline modules, without Docker.

**Architecture:** Keep the Phase 1 pipeline intact and add a dedicated Track A entrypoint that reuses the existing ORQA stack: `task_loader`, `llm_client`, `agent_runner`, `evaluator`, and `error_analyzer`. Add the two new skill conditions to the shared routing layer, then generate a Track A specific report so we do not contort the Phase 1 report generator around `v0_self_generated` and `v2_optimized` assumptions.

**Tech Stack:** Python 3, PyYAML, tiktoken, Rich, OpenAI-compatible model clients, pytest

---

### Task 1: Add Track A Condition Routing

**Files:**
- Modify: `src/skill_manager.py`
- Modify: `src/agent_runner.py`
- Modify: `tests/test_skill_manager.py`
- Modify: `tests/test_pipeline_smoke.py`

**Step 1: Write the failing tests for the new condition names**

Add tests that assert:
- `get_skill_for_condition("v1_component_minimal", "or_model_identification")` loads `skills/orqa/v1_component_minimal/or_model_identification.yaml`
- `get_skill_for_condition("v1_component_enriched", "or_model_identification")` loads `skills/orqa/v1_component_enriched/or_model_identification.yaml`
- `build_prompt(question, "v1_component_minimal", skill)` succeeds
- `build_prompt(question, "v1_component_enriched", skill)` succeeds

**Step 2: Run the targeted tests to verify they fail**

Run:
```bash
pytest tests/test_skill_manager.py tests/test_pipeline_smoke.py -q
```

Expected:
- `Unknown condition` failures for the two new Track A condition names

**Step 3: Add the new condition mappings**

In `src/skill_manager.py`:
- extend `_CONDITION_PATHS` with:
  - `v1_component_minimal -> skills/orqa/v1_component_minimal/{task_type}.yaml`
  - `v1_component_enriched -> skills/orqa/v1_component_enriched/{task_type}.yaml`

In `src/agent_runner.py`:
- extend `_SKILL_CONDITIONS` to include both new Track A skill conditions
- update docstrings/comments so valid condition lists are accurate

**Step 4: Run the targeted tests to verify they pass**

Run:
```bash
pytest tests/test_skill_manager.py tests/test_pipeline_smoke.py -q
```

Expected:
- PASS

**Step 5: Commit**

```bash
git add src/skill_manager.py src/agent_runner.py tests/test_skill_manager.py tests/test_pipeline_smoke.py
git commit -m "feat: add ORQA Track A condition routing"
```

### Task 2: Add a Dedicated Track A Runner

**Files:**
- Create: `src/run_track_a.py`
- Modify: `README.md`

**Step 1: Write the failing test for Track A condition selection**

Create a small test file for helper logic in the new runner, for example:
- Track A condition order is exactly:
  - `baseline`
  - `generic_scaffold`
  - `v1_curated`
  - `v1_component_minimal`
  - `v1_component_enriched`
- the runner does not reference `v0_self_generated` or `v2_optimized`

If the runner exposes helpers such as `TRACK_A_CONDITIONS` or `get_track_a_conditions()`, test those directly.

**Step 2: Run the new targeted test to verify it fails**

Run:
```bash
pytest tests/test_run_track_a.py -q
```

Expected:
- import failure because `src/run_track_a.py` does not yet exist

**Step 3: Write the minimal Track A runner**

Create `src/run_track_a.py` that:
- accepts `--model` and `--run-id`
- writes `results/runs/{run_id}/metadata.json`
- loads all ORQA questions and validates the split
- runs these conditions on `dev` and `test`:
  - `baseline`
  - `generic_scaffold`
  - `v1_curated`
  - `v1_component_minimal`
  - `v1_component_enriched`
- uses `get_skill_for_condition()` for all non-baseline conditions
- saves evaluations under:
  - `results/runs/{run_id}/evaluations/dev/*.json`
  - `results/runs/{run_id}/evaluations/test/*.json`
- runs `analyze_dev_failures()` on the dev results
- does not call `generate_skill()` or `optimize_skill()`

Also update `README.md` quick-start usage with a Track A command:
```bash
python -m src.run_track_a --model step_2_mini
```

**Step 4: Run the targeted tests to verify they pass**

Run:
```bash
pytest tests/test_run_track_a.py -q
```

Expected:
- PASS

**Step 5: Commit**

```bash
git add src/run_track_a.py README.md tests/test_run_track_a.py
git commit -m "feat: add dedicated ORQA Track A runner"
```

### Task 3: Add a Track A Specific Report Generator

**Files:**
- Create: `src/report_generator_track_a.py`
- Modify: `src/run_track_a.py`

**Step 1: Write the failing tests for Track A report content**

Add tests that assert the Track A report includes:
- the five Track A conditions
- dev and test accuracy tables
- paired comparison rows against `baseline`
- explicit comparison rows for:
  - `v1_component_minimal` vs `generic_scaffold`
  - `v1_component_enriched` vs `generic_scaffold`
  - `v1_component_minimal` vs `v1_curated`
  - `v1_component_enriched` vs `v1_curated`

**Step 2: Run the targeted tests to verify they fail**

Run:
```bash
pytest tests/test_report_generator_track_a.py -q
```

Expected:
- import failure or missing-section assertion failures

**Step 3: Implement the Track A report generator**

Create `src/report_generator_track_a.py` with helpers that:
- accept `dev_results`, `test_results`, `dev_analysis`, `questions`, `run_id`, `model_name`, and `dataset_label`
- write a markdown report into `results/runs/{run_id}/track_a_report.md`
- summarize:
  - dev accuracy
  - test accuracy
  - paired win/loss vs baseline
  - direct A1/A2 comparisons against scaffold and archetype skill
  - root-cause deltas on dev for the hard questions or the aggregate error taxonomy

Update `src/run_track_a.py` to call this report generator after test evaluation.

**Step 4: Run the targeted tests to verify they pass**

Run:
```bash
pytest tests/test_report_generator_track_a.py -q
```

Expected:
- PASS

**Step 5: Commit**

```bash
git add src/report_generator_track_a.py src/run_track_a.py tests/test_report_generator_track_a.py
git commit -m "feat: add ORQA Track A reporting"
```

### Task 4: Verify the Full Track A Path Locally

**Files:**
- Modify: `README.md`
- Optional create: `docs/08_track_a_results.md`

**Step 1: Run the local non-network verification suite**

Run:
```bash
pytest tests/test_skill_manager.py tests/test_pipeline_smoke.py tests/test_run_track_a.py tests/test_report_generator_track_a.py tests/test_contracts.py -q
```

Expected:
- PASS

**Step 2: Do a dry-run import verification**

Run:
```bash
python3 -m src.run_track_a --help
```

Expected:
- CLI help prints `--model` and `--run-id`

**Step 3: Document the production run commands**

Add exact commands to `README.md`:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 -m src.run_track_a --model step_2_mini --run-id track_a_stepfun_20260326
python3 -m src.run_track_a --model deepseek --run-id track_a_deepseek_20260326
```

Note in the docs that the required environment variables are:
- `STEPFUN_API_KEY` for `step_2_mini`
- `DEEPSEEK_API_KEY` for `deepseek`

**Step 4: Run the real Track A experiments**

Run StepFun first because the current repo evidence says it shows the clearest skill sensitivity:
```bash
python3 -m src.run_track_a --model step_2_mini --run-id track_a_stepfun_20260326
```

Then run DeepSeek for comparison:
```bash
python3 -m src.run_track_a --model deepseek --run-id track_a_deepseek_20260326
```

Expected artifacts:
- `results/runs/track_a_stepfun_20260326/metadata.json`
- `results/runs/track_a_stepfun_20260326/evaluations/dev/*.json`
- `results/runs/track_a_stepfun_20260326/evaluations/test/*.json`
- `results/runs/track_a_stepfun_20260326/analysis/dev_error_analysis.json`
- `results/runs/track_a_stepfun_20260326/track_a_report.md`
- same artifact pattern for DeepSeek

**Step 5: Commit**

```bash
git add README.md docs/08_track_a_results.md
git commit -m "docs: record ORQA Track A execution workflow"
```

### Task 5: Analyze and Write the Track A Result

**Files:**
- Create: `docs/08_track_a_results.md`

**Step 1: Summarize the held-out test table**

For each model, record:
- `baseline`
- `generic_scaffold`
- `v1_curated`
- `v1_component_minimal`
- `v1_component_enriched`

Use held-out `test` numbers as the primary evidence.

**Step 2: Apply the Track A decision rules from the spec**

State whether any of the following occurred:
- `A1 > baseline` and `A1 > scaffold`
- `A2 > baseline` and `A2 > scaffold`
- `A1 > v1_curated`
- `A2 > v1_curated`
- `A1` and `A2` changed the dev error pattern on the hard ORQA questions

**Step 3: Write the interpretation**

Possible conclusions:
- component-semantics skill content helps
- richer content does not help beyond the minimal targeted skill
- component-semantics does not outperform scaffold or archetype skill
- model sensitivity persists across StepFun and DeepSeek

**Step 4: Sanity-check the artifact references**

Verify every number in `docs/08_track_a_results.md` is copied from:
- `results/runs/<run_id>/evaluations/test/*.json`
- `results/runs/<run_id>/analysis/dev_error_analysis.json`
- `results/runs/<run_id>/track_a_report.md`

**Step 5: Commit**

```bash
git add docs/08_track_a_results.md
git commit -m "docs: add ORQA Track A ablation results"
```
